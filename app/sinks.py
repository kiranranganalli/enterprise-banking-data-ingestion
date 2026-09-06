from typing import Protocol

from app.models.transaction import Transaction


class TransactionSink(Protocol):

    def write(
        self,
        transaction: Transaction,
    ) -> bool:
        ...

    def write_batch(
        self,
        transactions: list[Transaction],
    ) -> set[str]:
        ...