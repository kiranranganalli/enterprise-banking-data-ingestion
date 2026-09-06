from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService


class RecordingSink:

    def __init__(self):
        self.batch_sizes = []

    def write(self, transaction):
        raise AssertionError(
            "write() should not be used when batch_size > 1"
        )

    def write_batch(self, transactions):
        self.batch_sizes.append(
            len(transactions)
        )

        return {
            transaction.idempotency_key
            for transaction in transactions
        }


def test_ingestion_service_writes_transactions_in_batches(
    tmp_path,
):
    input_file = tmp_path / "transactions.csv"
    rejected_file = tmp_path / "rejected.jsonl"

    input_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "8001,1,TRANSFER,100.00,C1,C2,0\n"
        "8002,1,PAYMENT,200.00,C3,M4,0\n"
        "8003,1,CASH_OUT,300.00,C5,C6,0\n"
        "8004,1,CASH_IN,400.00,C7,C8,0\n"
        "8005,1,DEBIT,500.00,C9,C10,0\n"
    )

    adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    sink = RecordingSink()

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
        sink=sink,
        batch_size=2,
    )

    result = service.ingest()

    assert result.accepted_count == 5

    assert result.duplicate_count == 0

    assert result.total_amount == 1500

    assert sink.batch_sizes == [
        2,
        2,
        1,
    ]