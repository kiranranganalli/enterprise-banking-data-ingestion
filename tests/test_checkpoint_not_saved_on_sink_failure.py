import pytest
from collections.abc import Iterator
from decimal import Decimal

from app.ingestion.base import SourceAdapter
from app.models.adapter_record import AdapterRecord
from app.models.enums import TransactionType
from app.models.page_complete import PageComplete
from app.models.transaction import Transaction
from app.services.ingestion_service import IngestionService


class FakeAPIAdapter(SourceAdapter):

    def read_transactions(
        self,
    ) -> Iterator[AdapterRecord | PageComplete]:

        yield AdapterRecord(
            transaction=Transaction(
                transaction_id="FAIL1001",
                transaction_type=TransactionType.TRANSFER,
                amount=Decimal("500.00"),
                source_account="C100",
                destination_account="C200",
                is_fraud=False,
            )
        )

        yield AdapterRecord(
            transaction=Transaction(
                transaction_id="FAIL1002",
                transaction_type=TransactionType.PAYMENT,
                amount=Decimal("250.00"),
                source_account="C300",
                destination_account="M400",
                is_fraud=False,
            )
        )

        yield PageComplete(
            next_page=2
        )


class FailingBatchSink:

    def write(self, transaction):
        raise AssertionError(
            "Single write should not be used"
        )

    def write_batch(self, transactions):
        raise RuntimeError(
            "Database unavailable"
        )


class RecordingCheckpointStore:

    def __init__(self):
        self.saved_pages = []

    def save_next_page(
        self,
        next_page,
    ):
        self.saved_pages.append(
            next_page
        )


def test_checkpoint_does_not_advance_when_batch_write_fails(
    tmp_path,
):
    adapter = FakeAPIAdapter()

    sink = FailingBatchSink()

    checkpoint_store = RecordingCheckpointStore()

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(
            tmp_path / "rejected.jsonl"
        ),
        sink=sink,
        checkpoint_store=checkpoint_store,
        batch_size=500,
    )

    with pytest.raises(
        RuntimeError,
        match="Database unavailable",
    ):
        service.ingest()

    assert checkpoint_store.saved_pages == []