import sqlite3
from decimal import Decimal

import pytest

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.sqlite_sink import SQLiteTransactionSink


def test_sink_does_not_silently_ignore_non_duplicate_constraint_failure(
    tmp_path,
):
    database_file = (
        tmp_path / "transactions.db"
    )

    sink = SQLiteTransactionSink(
        database_path=str(database_file)
    )

    transaction = Transaction(
        transaction_id="BAD1001",
        transaction_type=TransactionType.TRANSFER,
        amount=Decimal("500.00"),

        # Deliberately corrupt value.
        #
        # Transaction is a dataclass, so Python type
        # hints do not prevent None at runtime.
        source_account=None,  # type: ignore[arg-type]

        destination_account="C200",
        is_fraud=False,
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        sink.write(
            transaction
        )