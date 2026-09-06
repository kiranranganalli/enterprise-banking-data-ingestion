from decimal import Decimal, InvalidOperation


def validate_schema(
    actual_columns: set[str],
    required_columns: set[str],
) -> None:
    missing_columns = required_columns - actual_columns

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


def validate_transaction(
    transaction: dict[str, str]
) -> None:

    if not transaction["type"].strip():
        raise ValueError("transaction type is missing")

    if not transaction["nameOrig"].strip():
        raise ValueError("origin customer is missing")

    if not transaction["nameDest"].strip():
        raise ValueError("destination account is missing")

    try:
        amount = Decimal(transaction["amount"])
    except InvalidOperation as error:
        raise ValueError(
            f"invalid amount: {transaction['amount']}"
        ) from error

    if amount < 0:
        raise ValueError(
            f"negative amount: {amount}"
        )

    fraud_value = transaction["isFraud"]

    if fraud_value not in {"0", "1"}:
        raise ValueError(
            f"fraud flag must be 0 or 1: {fraud_value}"
        )