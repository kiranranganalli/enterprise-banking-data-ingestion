import sqlite3
from decimal import Decimal

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.sqlite_sink import SQLiteTransactionSink


def test_same_transaction_id_from_different_sources_can_both_be_stored(
    tmp_path,
):
    database_file = tmp_path / "transactions.db"

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    bank_a_transaction = Transaction(
        transaction_id="12345",
        transaction_type=TransactionType.TRANSFER,
        amount=Decimal("100.00"),
        source_account="A100",
        destination_account="A200",
        is_fraud=False,
        source_system="BANK_A",
    )

    bank_b_transaction = Transaction(
        transaction_id="12345",
        transaction_type=TransactionType.TRANSFER,
        amount=Decimal("900.00"),
        source_account="B100",
        destination_account="B200",
        is_fraud=False,
        source_system="BANK_B",
    )

    inserted_a = sink.write(
        bank_a_transaction
    )

    inserted_b = sink.write(
        bank_b_transaction
    )

    assert inserted_a is True

    # Desired behavior:
    # Same local ID from another source
    # should also be inserted.
    assert inserted_b is True

    with sqlite3.connect(
        database_file
    ) as connection:

        row_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            """
        ).fetchone()[0]

    assert row_count == 2