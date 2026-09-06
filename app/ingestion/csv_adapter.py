import json
from collections.abc import Iterator

from pydantic import ValidationError

from app.ingestion.base import SourceAdapter
from app.ingestion.csv_reader import (
    read_csv_headers,
    read_csv_records,
)
from app.models.adapter_record import AdapterRecord
from app.models.paysim import PaySimTransaction
from app.transformation.paysim import (
    normalize_paysim_transaction,
)
from app.validation import validate_schema


class CSVSourceAdapter(SourceAdapter):

    REQUIRED_COLUMNS = {
        "Unnamed: 0",
        "step",
        "type",
        "amount",
        "nameOrig",
        "nameDest",
        "isFraud",
    }

    def __init__(
        self,
        file_path: str,
        source_system: str = "PAYSIM",
    ):
        self.file_path = file_path
        self.source_system = source_system

    def read_transactions(
        self,
    ) -> Iterator[AdapterRecord]:

        headers = read_csv_headers(
            self.file_path
        )

        validate_schema(
            actual_columns=set(headers),
            required_columns=self.REQUIRED_COLUMNS,
        )

        for raw_record in read_csv_records(
            self.file_path
        ):

            try:
                source_transaction = (
                    PaySimTransaction.model_validate(
                        raw_record
                    )
                )

                transaction = (
                    normalize_paysim_transaction(
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