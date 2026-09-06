import sqlite3
from pathlib import Path


class SQLiteProcessedTransactionStore:

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

        self._create_table()

    def _connect(self):
        return sqlite3.connect(
            self.database_path
        )

    def _create_table(
        self,
    ) -> None:

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_transactions (
                    transaction_id TEXT PRIMARY KEY
                )
                """
            )

    def is_processed(
        self,
        transaction_id: str,
    ) -> bool:

        with self._connect() as connection:

            cursor = connection.execute(
                """
                SELECT 1
                FROM processed_transactions
                WHERE transaction_id = ?
                LIMIT 1
                """,
                (
                    transaction_id,
                ),
            )

            return (
                cursor.fetchone()
                is not None
            )

    def mark_processed(
        self,
        transaction_id: str,
    ) -> None:

        with self._connect() as connection:

            connection.execute(
                """
                INSERT OR IGNORE
                INTO processed_transactions (
                    transaction_id
                )
                VALUES (?)
                """,
                (
                    transaction_id,
                ),
            )

    def get_processed_ids(
        self,
        transaction_ids: list[str],
    ) -> set[str]:

        if not transaction_ids:
            return set()

        placeholders = ",".join(
            "?"
            for _ in transaction_ids
        )

        query = f"""
            SELECT transaction_id
            FROM processed_transactions
            WHERE transaction_id IN ({placeholders})
        """

        with self._connect() as connection:

            rows = connection.execute(
                query,
                transaction_ids,
            ).fetchall()

        return {
            row[0]
            for row in rows
        }

    def mark_processed_batch(
        self,
        transaction_ids: list[str],
    ) -> None:

        if not transaction_ids:
            return

        rows = [
            (
                transaction_id,
            )
            for transaction_id
            in transaction_ids
        ]

        with self._connect() as connection:

            connection.executemany(
                """
                INSERT OR IGNORE
                INTO processed_transactions (
                    transaction_id
                )
                VALUES (?)
                """,
                rows,
            )