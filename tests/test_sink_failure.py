from app.idempotency import ProcessedTransactionStore
from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService


class FailingSink:

    def write(self, transaction):
        raise RuntimeError(
            "Database write failed"
        )


def test_failed_sink_does_not_mark_transaction_as_processed(
    tmp_path,
):
    input_file = tmp_path / "transactions.csv"
    rejected_file = tmp_path / "rejected.jsonl"
    processed_file = tmp_path / "processed_ids.txt"

    input_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "7001,1,TRANSFER,500.00,C100,C200,0\n"
    )

    adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    processed_store = ProcessedTransactionStore(
        file_path=str(processed_file)
    )

    sink = FailingSink()

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
        processed_store=processed_store,
        sink=sink,
    )

    try:
        service.ingest()

    except RuntimeError as error:
        assert str(error) == "Database write failed"

    assert processed_store.is_processed(
        "7001"
    ) is False