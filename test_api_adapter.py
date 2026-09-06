from app.ingestion.api_adapter import APISourceAdapter


adapter = APISourceAdapter(
    url="http://localhost:8000/data/api_transactions.json"
)


for adapter_record in adapter.read_transactions():

    if adapter_record.is_valid:
        print(
            "VALID:",
            adapter_record.transaction
        )

    else:
        print(
            "REJECTED:",
            adapter_record.raw_record,
            adapter_record.errors,
        )