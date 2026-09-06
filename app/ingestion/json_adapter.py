import json
from collections.abc import Iterator

from pydantic import ValidationError

from app.ingestion.base import SourceAdapter
from app.ingestion.jsonl_reader import read_jsonl_records
from app.models.adapter_record import AdapterRecord
from app.models.partner_json import PartnerJSONTransaction
from app.transformation.partner_json import (
    normalize_partner_json_transaction,
)


class JSONSourceAdapter(SourceAdapter):

    def __init__(
        self,
        file_path: str,
        source_system: str = "PARTNER_JSON",
    ):
        self.file_path = file_path
        self.source_system = source_system

    def read_transactions(
        self,
    ) -> Iterator[AdapterRecord]:

        for raw_record in read_jsonl_records(
            self.file_path
        ):

            try:

                source_transaction = (
                    PartnerJSONTransaction.model_validate(
                        raw_record
                    )
                )

                transaction = (
                    normalize_partner_json_transaction(
                        source_transaction,
                        source_system=self.source_system,
                    )
                )

                yield AdapterRecord(
                    transaction=transaction
                )

            except ValidationError as error:

                json_safe_errors = json.loads(
                    error.json()
                )

                yield AdapterRecord(
                    raw_record=raw_record,
                    errors=json_safe_errors,
                )