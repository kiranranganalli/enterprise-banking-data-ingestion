from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TransactionType


class PaySimTransaction(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    transaction_id: str = Field(alias="Unnamed: 0")

    step: int
    type: TransactionType

    amount: Decimal = Field(ge=0)

    nameOrig: str
    nameDest: str

    isFraud: int = Field(ge=0, le=1)

    @field_validator("nameOrig", "nameDest")
    @classmethod
    def account_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("account cannot be empty")

        return value