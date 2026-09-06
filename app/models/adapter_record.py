from dataclasses import dataclass
from typing import Any

from app.models.transaction import Transaction


@dataclass
class AdapterRecord:
    transaction: Transaction | None = None
    raw_record: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None

    @property
    def is_valid(self) -> bool:
        return self.transaction is not None