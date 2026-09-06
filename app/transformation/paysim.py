from app.models.paysim import PaySimTransaction
from app.models.transaction import Transaction


def normalize_paysim_transaction(
    source: PaySimTransaction,
    source_system: str = "PAYSIM",
) -> Transaction:

    return Transaction(
        transaction_id=source.transaction_id,
        transaction_type=source.type,
        amount=source.amount,
        source_account=source.nameOrig,
        destination_account=source.nameDest,
        is_fraud=source.isFraud == 1,
        source_system=source_system,
    )