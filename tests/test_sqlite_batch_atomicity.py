import sqlite3
from decimal import Decimal

import pytest

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.sqlite_sink import SQLiteTransactionSink


def test_failed_batch_rolls_back_all_transactions(
    tmp_path,
):
    database_file = tmp_path / "transactions.db"

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    transactions = [
        Transaction(
            transaction_id="ATOMIC1001",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100.00"),
            source_account="C100",
            destination_account="C200",
            is_fraud=False,
        ),
        Transaction(
            transaction_id="ATOMIC1002",
            transaction_type=TransactionType.PAYMENT,
            amount=Decimal("200.00"),

            # Deliberately invalid.
            source_account=None,  # type: ignore[arg-type]

            destination_account="M300",
            is_fraud=False,
        ),
        Transaction(
            transaction_id="ATOMIC1003",
            transaction_type=TransactionType.CASH_OUT,
            amount=Decimal("300.00"),
            source_account="C400",
            destination_account="C500",
            is_fraud=False,
        ),
    ]

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        sink.write_batch(
            transactions
        )

    with sqlite3.connect(
        database_file
    ) as connection:

        rows = connection.execute(
            """
            SELECT transaction_id
            FROM transactions
            """
        ).fetchall()

    assert rows == []