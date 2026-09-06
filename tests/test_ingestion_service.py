import json
from decimal import Decimal

from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService


def test_ingestion_service_processes_valid_and_invalid_records(tmp_path):
    input_file = tmp_path / "transactions.csv"
    rejected_file = tmp_path / "rejected.jsonl"

    input_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "1001,1,TRANSFER,250.50,C100,C200,0\n"
        "1002,2,PAYMENT,100.00,C101,M300,0\n"
        "1003,3,CASH_OUT,-50.00,C102,C400,0\n"
    )

    adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert result.accepted_count == 2
    assert result.rejected_count == 1

    assert result.total_amount == Decimal("350.50")

    assert result.transaction_type_counts == {
        "TRANSFER": 1,
        "PAYMENT": 1,
    }

    assert result.fraud_count == 0
    assert result.fraud_amount == Decimal("0")

    rejected_lines = rejected_file.read_text().splitlines()

    assert len(rejected_lines) == 1

    rejected_record = json.loads(rejected_lines[0])

    assert (
        rejected_record["transaction"]["Unnamed: 0"]
        == "1003"
    )