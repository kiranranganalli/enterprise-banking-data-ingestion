import sqlite3
from pathlib import Path

from app.models.transaction import Transaction


class SQLiteTransactionSink:

    def __init__(
        self,
        database_path: str,
    ):
        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(
            self.database_path
        )

    def _create_transactions_table(
        self,
        connection,
    ) -> None:

        connection.execute(
            """
            CREATE TABLE transactions (
                source_system TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                source_account TEXT NOT NULL,
                destination_account TEXT NOT NULL,
                is_fraud INTEGER NOT NULL,

                PRIMARY KEY (
                    source_system,
                    transaction_id
                )
            )
            """
        )

    def _ensure_schema(
        self,
    ) -> None:

        with self._connect() as connection:

            # ------------------------------------------
            # Does the transactions table already exist?
            # ------------------------------------------

            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'transactions'
                """
            ).fetchone()

            # ------------------------------------------
            # Fresh database
            # ------------------------------------------

            if table_exists is None:

                self._create_transactions_table(
                    connection
                )

                return

            # ------------------------------------------
            # Inspect existing schema
            # ------------------------------------------

            columns = connection.execute(
                """
                PRAGMA table_info(transactions)
                """
            ).fetchall()

            column_names = {
                column[1]
                for column in columns
            }

            # PRAGMA table_info:
            #
            # column[1] = column name
            # column[5] = primary-key position
            #
            # New schema should have:
            #
            # source_system  -> PK position 1
            # transaction_id -> PK position 2

            primary_key_columns = [
                column[1]
                for column in sorted(
                    columns,
                    key=lambda column: column[5],
                )
                if column[5] > 0
            ]

            expected_primary_key = [
                "source_system",
                "transaction_id",
            ]

            # ------------------------------------------
            # Already using current schema
            # ------------------------------------------

            if (
                "source_system" in column_names
                and primary_key_columns
                == expected_primary_key
            ):
                return

            # ------------------------------------------
            # Old schema detected
            # ------------------------------------------

            self._migrate_schema(
                connection=connection,
                column_names=column_names,
            )

    def _migrate_schema(
        self,
        connection,
        column_names: set[str],
    ) -> None:

        # ------------------------------------------
        # Rename old table
        # ------------------------------------------

        connection.execute(
            """
            ALTER TABLE transactions
            RENAME TO transactions_old
            """
        )

        # ------------------------------------------
        # Create new table
        # ------------------------------------------

        self._create_transactions_table(
            connection
        )

        # ------------------------------------------
        # Copy old data
        # ------------------------------------------

        if "source_system" in column_names:

            # Intermediate schema already had
            # source_system, so preserve it.

            connection.execute(
                """
                INSERT INTO transactions (
                    source_system,
                    transaction_id,
                    transaction_type,
                    amount,
                    source_account,
                    destination_account,
                    is_fraud
                )
                SELECT
                    source_system,
                    transaction_id,
                    transaction_type,
                    amount,
                    source_account,
                    destination_account,
                    is_fraud
                FROM transactions_old
                """
            )

        else:

            # Very old schema had no source information.
            #
            # We cannot safely guess where those records
            # originally came from, so label them LEGACY.

            connection.execute(
                """
                INSERT INTO transactions (
                    source_system,
                    transaction_id,
                    transaction_type,
                    amount,
                    source_account,
                    destination_account,
                    is_fraud
                )
                SELECT
                    'LEGACY',
                    transaction_id,
                    transaction_type,
                    amount,
                    source_account,
                    destination_account,
                    is_fraud
                FROM transactions_old
                """
            )

        # ------------------------------------------
        # Remove old table only after copy succeeds
        # ------------------------------------------

        connection.execute(
            """
            DROP TABLE transactions_old
            """
        )

    def write(
        self,
        transaction: Transaction,
    ) -> bool:

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO transactions (
                    source_system,
                    transaction_id,
                    transaction_type,
                    amount,
                    source_account,
                    destination_account,
                    is_fraud
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(
                    source_system,
                    transaction_id
                )
                DO NOTHING
                """,
                (
                    transaction.source_system,
                    transaction.transaction_id,
                    transaction.transaction_type.value,
                    str(transaction.amount),
                    transaction.source_account,
                    transaction.destination_account,
                    int(transaction.is_fraud),
                ),
            )

            return cursor.rowcount == 1

    def write_batch(
        self,
        transactions: list[Transaction],
    ) -> set[str]:

        if not transactions:
            return set()

        inserted_keys: set[str] = set()

        with self._connect() as connection:

            for transaction in transactions:

                cursor = connection.execute(
                    """
                    INSERT INTO transactions (
                        source_system,
                        transaction_id,
                        transaction_type,
                        amount,
                        source_account,
                        destination_account,
                        is_fraud
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(
                        source_system,
                        transaction_id
                    )
                    DO NOTHING
                    """,
                    (
                        transaction.source_system,
                        transaction.transaction_id,
                        transaction.transaction_type.value,
                        str(transaction.amount),
                        transaction.source_account,
                        transaction.destination_account,
                        int(transaction.is_fraud),
                    ),
                )

                if cursor.rowcount == 1:

                    inserted_keys.add(
                        transaction.idempotency_key
                    )

        return inserted_keys