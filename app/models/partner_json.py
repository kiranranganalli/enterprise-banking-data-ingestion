from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TransactionType


class PartnerJSONTransaction(BaseModel):
    transaction_id: str
    transaction_type: TransactionType
    transaction_amount: Decimal = Field(ge=0)
    source_account: str
    destination_account: str
    fraud_flag: int = Field(ge=0, le=1)

    @field_validator("source_account", "destination_account")
    @classmethod
    def account_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("account cannot be empty")

        return value