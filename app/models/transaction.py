from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import TransactionType


@dataclass
class Transaction:

    transaction_id: str
    transaction_type: TransactionType
    amount: Decimal
    source_account: str
    destination_account: str
    is_fraud: bool
    source_system: str = "UNKNOWN"

    @property
    def idempotency_key(
        self,
    ) -> str:

        return (
            f"{self.source_system}:"
            f"{self.transaction_id}"
        )