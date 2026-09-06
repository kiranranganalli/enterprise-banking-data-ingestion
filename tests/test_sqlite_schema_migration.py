import sqlite3
from decimal import Decimal

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.sqlite_sink import SQLiteTransactionSink


def test_old_transaction_schema_is_migrated(
    tmp_path,
):
    database_file = tmp_path / "transactions.db"

    # ------------------------------------------------
    # Simulate database created by our OLD application
    # ------------------------------------------------

    with sqlite3.connect(
        database_file
    ) as connection:

        connection.execute(
            """
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                transaction_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                source_account TEXT NOT NULL,
                destination_account TEXT NOT NULL,
                is_fraud INTEGER NOT NULL
            )
            """
        )

        connection.execute(
            """
            INSERT INTO transactions (
                transaction_id,
                transaction_type,
                amount,
                source_account,
                destination_account,
                is_fraud
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "OLD1001",
                "TRANSFER",
                "100.00",
                "C100",
                "C200",
                0,
            ),
        )

    # ------------------------------------------------
    # Start NEW version of our sink
    # ------------------------------------------------

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    new_transaction = Transaction(
        transaction_id="NEW1001",
        transaction_type=TransactionType.PAYMENT,
        amount=Decimal("250.00"),
        source_account="C300",
        destination_account="M400",
        is_fraud=False,
        source_system="PAYSIM",
    )

    inserted = sink.write(
        new_transaction
    )

    assert inserted is True

    # ------------------------------------------------
    # Verify new schema
    # ------------------------------------------------

    with sqlite3.connect(
        database_file
    ) as connection:

        columns = connection.execute(
            """
            PRAGMA table_info(transactions)
            """
        ).fetchall()

        rows = connection.execute(
            """
            SELECT
                source_system,
                transaction_id
            FROM transactions
            ORDER BY
                source_system,
                transaction_id
            """
        ).fetchall()

    column_names = {
        column[1]
        for column in columns
    }

    assert "source_system" in column_names

    assert rows == [
        (
            "LEGACY",
            "OLD1001",
        ),
        (
            "PAYSIM",
            "NEW1001",
        ),
    ]