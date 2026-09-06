from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.enums import TransactionType
from app.models.paysim import PaySimTransaction


def valid_transaction():
    return {
        "Unnamed: 0": "12345",
        "step": "100",
        "type": "TRANSFER",
        "amount": "250.75",
        "nameOrig": "C100",
        "nameDest": "C200",
        "isFraud": "0",
    }


def test_valid_transaction_is_parsed():
    raw = valid_transaction()

    transaction = PaySimTransaction.model_validate(raw)

    assert transaction.transaction_id == "12345"
    assert transaction.step == 100
    assert transaction.type == TransactionType.TRANSFER
    assert transaction.amount == Decimal("250.75")
    assert transaction.nameOrig == "C100"
    assert transaction.nameDest == "C200"
    assert transaction.isFraud == 0


def test_negative_amount_is_rejected():
    raw = valid_transaction()
    raw["amount"] = "-100.00"

    with pytest.raises(ValidationError):
        PaySimTransaction.model_validate(raw)


def test_invalid_amount_is_rejected():
    raw = valid_transaction()
    raw["amount"] = "NOT_A_NUMBER"

    with pytest.raises(ValidationError):
        PaySimTransaction.model_validate(raw)


def test_invalid_transaction_type_is_rejected():
    raw = valid_transaction()
    raw["type"] = "WIRE_TRANSFER"

    with pytest.raises(ValidationError):
        PaySimTransaction.model_validate(raw)


def test_invalid_fraud_flag_is_rejected():
    raw = valid_transaction()
    raw["isFraud"] = "7"

    with pytest.raises(ValidationError):
        PaySimTransaction.model_validate(raw)


def test_empty_origin_account_is_rejected():
    raw = valid_transaction()
    raw["nameOrig"] = "   "

    with pytest.raises(ValidationError):
        PaySimTransaction.model_validate(raw)