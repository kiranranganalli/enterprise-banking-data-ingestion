import sqlite3
from decimal import Decimal

from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService
from app.sqlite_sink import SQLiteTransactionSink


def test_ingestion_writes_valid_transactions_to_sqlite(
    tmp_path,
):
    input_file = tmp_path / "transactions.csv"
    rejected_file = tmp_path / "rejected.jsonl"
    database_file = tmp_path / "transactions.db"

    input_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "1001,1,TRANSFER,250.50,C100,C200,0\n"
        "1002,2,PAYMENT,100.00,C101,M300,0\n"
        "1003,3,CASH_OUT,-50.00,C102,C400,0\n"
    )

    adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
        sink=sink,
    )

    result = service.ingest()

    assert result.accepted_count == 2
    assert result.rejected_count == 1
    assert result.total_amount == Decimal("350.50")

    # -----------------------------------------
    # Inspect what was actually written
    # -----------------------------------------

    with sqlite3.connect(database_file) as connection:

        rows = connection.execute(
            """
            SELECT
                transaction_id,
                transaction_type,
                amount,
                source_account,
                destination_account,
                is_fraud
            FROM transactions
            ORDER BY transaction_id
            """
        ).fetchall()

    assert rows == [
        (
            "1001",
            "TRANSFER",
            "250.50",
            "C100",
            "C200",
            0,
        ),
        (
            "1002",
            "PAYMENT",
            "100.00",
            "C101",
            "M300",
            0,
        ),
    ]