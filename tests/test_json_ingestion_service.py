import json
from decimal import Decimal

from app.ingestion.json_adapter import JSONSourceAdapter
from app.services.ingestion_service import IngestionService


def test_json_ingestion_service_processes_valid_and_invalid_records(
    tmp_path,
):
    input_file = tmp_path / "transactions.jsonl"
    rejected_file = tmp_path / "rejected.jsonl"

    records = [
        {
            "transaction_id": "2001",
            "transaction_type": "TRANSFER",
            "transaction_amount": "300.00",
            "source_account": "C100",
            "destination_account": "C200",
            "fraud_flag": "0",
        },
        {
            "transaction_id": "2002",
            "transaction_type": "PAYMENT",
            "transaction_amount": "150.50",
            "source_account": "C101",
            "destination_account": "M300",
            "fraud_flag": "0",
        },
        {
            "transaction_id": "2003",
            "transaction_type": "CASH_OUT",
            "transaction_amount": "-25.00",
            "source_account": "C102",
            "destination_account": "C400",
            "fraud_flag": "0",
        },
    ]

    with open(input_file, "w") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")

    adapter = JSONSourceAdapter(
        file_path=str(input_file)
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert result.accepted_count == 2
    assert result.rejected_count == 1
    assert result.total_amount == Decimal("450.50")

    assert result.transaction_type_counts == {
        "TRANSFER": 1,
        "PAYMENT": 1,
    }

    rejected_lines = rejected_file.read_text().splitlines()

    assert len(rejected_lines) == 1

    rejected_record = json.loads(rejected_lines[0])

    assert (
        rejected_record["transaction"]["transaction_id"]
        == "2003"
    )