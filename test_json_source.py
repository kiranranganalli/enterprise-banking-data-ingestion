from app.ingestion.json_reader import read_json_records
from app.models.partner_json import PartnerJSONTransaction
from app.transformation.partner_json import (
    normalize_partner_json_transaction,
)


for raw_record in read_json_records(
    "data/partner_transactions.json"
):
    source = PartnerJSONTransaction.model_validate(
        raw_record
    )

    transaction = normalize_partner_json_transaction(
        source
    )

    print(transaction)
    print(type(transaction))

    break