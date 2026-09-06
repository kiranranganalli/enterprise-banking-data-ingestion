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
                transaction_id="PAGE1001",
                transaction_type=TransactionType.TRANSFER,
                amount=Decimal("100.00"),
                source_account="C1",
                destination_account="C2",
                is_fraud=False,
                source_system="TEST_API",
            )
        )

        yield AdapterRecord(
            transaction=Transaction(
                transaction_id="PAGE1002",
                transaction_type=TransactionType.PAYMENT,
                amount=Decimal("200.00"),
                source_account="C3",
                destination_account="M4",
                is_fraud=False,
                source_system="TEST_API",
            )
        )

        yield PageComplete(
            next_page=2
        )


class RecordingSink:

    def __init__(self, events):
        self.events = events

    def write(self, transaction):
        raise AssertionError(
            "Single write should not be used"
        )

    def write_batch(self, transactions):
        self.events.append(
            f"sink:{len(transactions)}"
        )

        return {
            transaction.idempotency_key
            for transaction in transactions
        }


class RecordingCheckpointStore:

    def __init__(self, events):
        self.events = events

    def save_next_page(
        self,
        next_page,
    ):
        self.events.append(
            f"checkpoint:{next_page}"
        )


def test_batch_is_written_before_checkpoint_advances(
    tmp_path,
):
    events = []

    adapter = FakeAPIAdapter()

    sink = RecordingSink(
        events=events
    )

    checkpoint_store = RecordingCheckpointStore(
        events=events
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(
            tmp_path / "rejected.jsonl"
        ),
        sink=sink,
        checkpoint_store=checkpoint_store,
        batch_size=500,
    )

    result = service.ingest()

    assert result.accepted_count == 2

    assert result.duplicate_count == 0

    assert events == [
        "sink:2",
        "checkpoint:2",
    ]