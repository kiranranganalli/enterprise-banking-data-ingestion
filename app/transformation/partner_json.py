from app.models.partner_json import PartnerJSONTransaction
from app.models.transaction import Transaction


def normalize_partner_json_transaction(
    source: PartnerJSONTransaction,
    source_system: str = "PARTNER_JSON",
) -> Transaction:

    return Transaction(
        transaction_id=source.transaction_id,
        transaction_type=source.transaction_type,
        amount=source.transaction_amount,
        source_account=source.source_account,
        destination_account=source.destination_account,
        is_fraud=source.fraud_flag == 1,
        source_system=source_system,
    )