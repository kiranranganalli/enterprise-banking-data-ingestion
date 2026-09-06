from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class IngestionResult:
    accepted_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0

    total_amount: Decimal = Decimal("0")

    transaction_type_counts: dict[str, int] = field(
        default_factory=dict
    )

    fraud_count: int = 0
    fraud_amount: Decimal = Decimal("0")

    @property
    def fraud_percentage(self) -> float:
        if self.accepted_count == 0:
            return 0.0

        return (
            self.fraud_count
            / self.accepted_count
        ) * 100