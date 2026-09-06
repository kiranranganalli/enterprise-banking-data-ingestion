import json
import logging
import time

from app.checkpoint import CheckpointStore
from app.idempotency import ProcessedStore
from app.ingestion.base import SourceAdapter
from app.models.ingestion_result import IngestionResult
from app.models.page_complete import PageComplete
from app.models.transaction import Transaction
from app.sinks import TransactionSink


logger = logging.getLogger(__name__)


class IngestionService:

    def __init__(
        self,
        adapter: SourceAdapter,
        rejected_file_path: str,
        processed_store: ProcessedStore | None = None,
        sink: TransactionSink | None = None,
        checkpoint_store: CheckpointStore | None = None,
        batch_size: int = 1,
    ):
        self.adapter = adapter
        self.rejected_file_path = rejected_file_path
        self.processed_store = processed_store
        self.sink = sink
        self.batch_size = batch_size

        self.checkpoint_store = (
            checkpoint_store
            if checkpoint_store is not None
            else getattr(
                adapter,
                "checkpoint_store",
                None,
            )
        )

    def _update_result(
        self,
        result: IngestionResult,
        transaction: Transaction,
    ) -> None:

        result.accepted_count += 1
        result.total_amount += transaction.amount

        transaction_type = (
            transaction.transaction_type.value
        )

        if (
            transaction_type
            in result.transaction_type_counts
        ):
            result.transaction_type_counts[
                transaction_type
            ] += 1

        else:
            result.transaction_type_counts[
                transaction_type
            ] = 1

        if transaction.is_fraud:
            result.fraud_count += 1
            result.fraud_amount += (
                transaction.amount
            )

    def _flush_batch(
        self,
        batch: list[Transaction],
        pending_ids: set[str],
        result: IngestionResult,
    ) -> None:

        if not batch:
            return

        # ------------------------------------------
        # 1. Build source-scoped idempotency keys
        # ------------------------------------------

        batch_ids = [
            transaction.idempotency_key
            for transaction in batch
        ]

        # ------------------------------------------
        # 2. Find already-processed IDs in one query
        # ------------------------------------------

        if self.processed_store is not None:

            processed_ids = (
                self.processed_store.get_processed_ids(
                    batch_ids
                )
            )

        else:
            processed_ids = set()

        # ------------------------------------------
        # 3. Already-processed records are duplicates
        # ------------------------------------------

        result.duplicate_count += len(
            processed_ids
        )

        transactions_to_write = [
            transaction
            for transaction in batch
            if transaction.idempotency_key
            not in processed_ids
        ]

        # ------------------------------------------
        # Nothing new to write
        # ------------------------------------------

        if not transactions_to_write:

            batch.clear()
            pending_ids.clear()
            return

        # ------------------------------------------
        # 4. Write transactions to destination
        # ------------------------------------------

        if self.sink is None:

            inserted_ids = {
                transaction.idempotency_key
                for transaction
                in transactions_to_write
            }

        elif self.batch_size == 1:

            transaction = (
                transactions_to_write[0]
            )

            inserted = self.sink.write(
                transaction
            )

            inserted_ids = (
                {
                    transaction.idempotency_key
                }
                if inserted
                else set()
            )

        else:

            inserted_ids = (
                self.sink.write_batch(
                    transactions_to_write
                )
            )

        # ------------------------------------------
        # 5. Determine inserted vs existing in sink
        # ------------------------------------------

        durable_ids: list[str] = []

        for transaction in transactions_to_write:

            idempotency_key = (
                transaction.idempotency_key
            )

            if idempotency_key in inserted_ids:

                # Newly inserted during this run.
                self._update_result(
                    result,
                    transaction,
                )

            else:

                # Already existed in sink.
                #
                # Possible crash-recovery scenario:
                #
                # sink write succeeds
                # ↓
                # app crashes before idempotency mark
                # ↓
                # restart sees transaction again
                result.duplicate_count += 1

            # Newly inserted OR already existing
            # means the destination contains it.
            durable_ids.append(
                idempotency_key
            )

        # ------------------------------------------
        # 6. Mark durable transactions processed
        #    in one batch operation
        # ------------------------------------------

        if self.processed_store is not None:

            self.processed_store.mark_processed_batch(
                durable_ids
            )

        # ------------------------------------------
        # Batch finished successfully
        # ------------------------------------------

        batch.clear()
        pending_ids.clear()

    def ingest(
        self,
    ) -> IngestionResult:

        start_time = time.perf_counter()

        logger.info(
            "Starting ingestion adapter=%s",
            self.adapter.__class__.__name__,
        )

        result = IngestionResult()

        batch: list[Transaction] = []
        pending_ids: set[str] = set()

        with open(
            self.rejected_file_path,
            "w",
        ) as rejected_file:

            for item in self.adapter.read_transactions():

                # ------------------------------------------
                # API page completed
                # ------------------------------------------

                if isinstance(
                    item,
                    PageComplete,
                ):

                    # First make page transactions durable.
                    self._flush_batch(
                        batch,
                        pending_ids,
                        result,
                    )

                    # Only after successful persistence
                    # should the checkpoint move forward.
                    if self.checkpoint_store is not None:

                        self.checkpoint_store.save_next_page(
                            item.next_page
                        )

                    continue

                adapter_record = item

                # ------------------------------------------
                # Rejected record
                # ------------------------------------------

                if not adapter_record.is_valid:

                    rejected_record = {
                        "transaction": (
                            adapter_record.raw_record
                        ),
                        "errors": (
                            adapter_record.errors
                        ),
                    }

                    rejected_file.write(
                        json.dumps(
                            rejected_record
                        )
                        + "\n"
                    )

                    result.rejected_count += 1
                    continue

                transaction = (
                    adapter_record.transaction
                )

                # ------------------------------------------
                # Duplicate inside current memory batch
                # ------------------------------------------

                if (
                    transaction.idempotency_key
                    in pending_ids
                ):

                    result.duplicate_count += 1
                    continue

                # ------------------------------------------
                # Add transaction to batch
                # ------------------------------------------

                batch.append(
                    transaction
                )

                pending_ids.add(
                    transaction.idempotency_key
                )

                # ------------------------------------------
                # Flush when batch reaches configured size
                # ------------------------------------------

                if len(batch) >= self.batch_size:

                    self._flush_batch(
                        batch,
                        pending_ids,
                        result,
                    )

            # ------------------------------------------
            # Flush final CSV / JSONL partial batch
            # ------------------------------------------

            self._flush_batch(
                batch,
                pending_ids,
                result,
            )

        # ------------------------------------------
        # Performance
        # ------------------------------------------

        duration = (
            time.perf_counter()
            - start_time
        )

        total_records = (
            result.accepted_count
            + result.rejected_count
            + result.duplicate_count
        )

        records_per_second = (
            total_records / duration
            if duration > 0
            else 0
        )

        # ------------------------------------------
        # Logging
        # ------------------------------------------

        if result.rejected_count > 0:

            logger.warning(
                (
                    "Ingestion contains rejected records "
                    "count=%s rejected_file=%s"
                ),
                result.rejected_count,
                self.rejected_file_path,
            )

        if result.duplicate_count > 0:

            logger.info(
                (
                    "Ingestion skipped duplicate records "
                    "count=%s"
                ),
                result.duplicate_count,
            )

        logger.info(
            (
                "Ingestion completed "
                "adapter=%s "
                "accepted=%s "
                "rejected=%s "
                "duplicates=%s "
                "total_amount=%s"
            ),
            self.adapter.__class__.__name__,
            result.accepted_count,
            result.rejected_count,
            result.duplicate_count,
            result.total_amount,
        )

        logger.info(
            (
                "Ingestion performance "
                "duration_seconds=%.4f "
                "records_processed=%s "
                "records_per_second=%.2f"
            ),
            duration,
            total_records,
            records_per_second,
        )

        return result