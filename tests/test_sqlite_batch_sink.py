import sqlite3
from decimal import Decimal

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.sqlite_sink import SQLiteTransactionSink


def test_sqlite_sink_writes_transaction_batch(
    tmp_path,
):
    database_file = tmp_path / "transactions.db"

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    transactions = [
        Transaction(
            transaction_id="BATCH1001",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100.00"),
            source_account="C100",
            destination_account="C200",
            is_fraud=False,
        ),
        Transaction(
            transaction_id="BATCH1002",
            transaction_type=TransactionType.PAYMENT,
            amount=Decimal("200.00"),
            source_account="C300",
            destination_account="M400",
            is_fraud=False,
        ),
        Transaction(
            transaction_id="BATCH1003",
            transaction_type=TransactionType.CASH_OUT,
            amount=Decimal("300.00"),
            source_account="C500",
            destination_account="C600",
            is_fraud=True,
        ),
    ]

    sink.write_batch(
        transactions
    )

    with sqlite3.connect(database_file) as connection:

        rows = connection.execute(
            """
            SELECT
                transaction_id,
                transaction_type,
                amount,
                is_fraud
            FROM transactions
            ORDER BY transaction_id
            """
        ).fetchall()

    assert rows == [
        (
            "BATCH1001",
            "TRANSFER",
            "100.00",
            0,
        ),
        (
            "BATCH1002",
            "PAYMENT",
            "200.00",
            0,
        ),
        (
            "BATCH1003",
            "CASH_OUT",
            "300.00",
            1,
        ),
    ]