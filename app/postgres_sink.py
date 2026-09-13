import psycopg

from app.models.transaction import Transaction


class PostgresTransactionSink:

    def __init__(
        self,
        database_url: str,
    ):
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(
            self.database_url
        )

    def write(
        self,
        transaction: Transaction,
    ) -> bool:

        with self._connect() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO banking.ingested_transactions (
                        source_system,
                        transaction_id,
                        transaction_type,
                        amount,
                        source_account,
                        destination_account,
                        is_fraud
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        source_system,
                        transaction_id
                    )
                    DO NOTHING
                    """,
                    (
                        transaction.source_system,
                        transaction.transaction_id,
                        transaction.transaction_type.value,
                        transaction.amount,
                        transaction.source_account,
                        transaction.destination_account,
                        transaction.is_fraud,
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

            with connection.cursor() as cursor:

                for transaction in transactions:

                    cursor.execute(
                        """
                        INSERT INTO banking.ingested_transactions (
                            source_system,
                            transaction_id,
                            transaction_type,
                            amount,
                            source_account,
                            destination_account,
                            is_fraud
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )

                        ON CONFLICT (
                            source_system,
                            transaction_id
                        )
                        DO NOTHING
                        """,
                        (
                            transaction.source_system,
                            transaction.transaction_id,
                            transaction.transaction_type.value,
                            transaction.amount,
                            transaction.source_account,
                            transaction.destination_account,
                            transaction.is_fraud,
                        ),
                    )

                    if cursor.rowcount == 1:

                        inserted_keys.add(
                            transaction.idempotency_key
                        )

        return inserted_keys
