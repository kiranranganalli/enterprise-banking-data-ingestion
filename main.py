from app.checkpoint import CheckpointStore
from app.config import Settings
from app.ingestion.factory import create_source_adapter
from app.logging_config import configure_logging
from app.postgres_sink import PostgresTransactionSink
from app.services.ingestion_service import IngestionService
from app.sqlite_idempotency import SQLiteProcessedTransactionStore
from app.sqlite_sink import SQLiteTransactionSink


# ------------------------------------------
# Logging
# ------------------------------------------

configure_logging()


# ------------------------------------------
# Configuration
# ------------------------------------------

settings = Settings()


# ------------------------------------------
# Resolve effective source system
# ------------------------------------------

default_source_systems = {
    "csv": "PAYSIM",
    "json": "PARTNER_JSON",
    "api": "PARTNER_API",
}

source_type = settings.source_type.lower()

if source_type not in default_source_systems:
    raise ValueError(
        f"Unsupported source type: "
        f"{settings.source_type}"
    )

effective_source_system = (
    settings.source_system
    or default_source_systems[source_type]
)


# ------------------------------------------
# Checkpoint state
# ------------------------------------------

checkpoint_store = CheckpointStore(
    file_path=settings.checkpoint_file_path,
    source_system=effective_source_system,
)


# ------------------------------------------
# Idempotency state
# ------------------------------------------

processed_store = SQLiteProcessedTransactionStore(
    database_path=settings.idempotency_database_path
)


# ------------------------------------------
# Destination database
# ------------------------------------------

database_backend = settings.database_backend.lower()

if database_backend == "sqlite":

    transaction_sink = SQLiteTransactionSink(
        database_path=settings.transaction_database_path
    )

elif database_backend == "postgres":

    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL is required "
            "when DATABASE_BACKEND=postgres"
        )

    transaction_sink = PostgresTransactionSink(
        database_url=settings.database_url
    )

else:
    raise ValueError(
        f"Unsupported database backend: "
        f"{settings.database_backend}"
    )


# ------------------------------------------
# Source
# ------------------------------------------

adapter = create_source_adapter(
    source_type=source_type,
    file_path=settings.input_file_path,
    api_url=settings.api_url,
    checkpoint_store=checkpoint_store,
    source_system=effective_source_system,
    api_token=settings.api_token,
)


# ------------------------------------------
# Ingestion orchestration
# ------------------------------------------

service = IngestionService(
    adapter=adapter,
    rejected_file_path=settings.rejected_file_path,
    processed_store=processed_store,
    sink=transaction_sink,
    checkpoint_store=checkpoint_store,
    batch_size=settings.batch_size,
)


# ------------------------------------------
# Execute
# ------------------------------------------

result = service.ingest()


# ------------------------------------------
# Summary
# ------------------------------------------

print()
print("Ingestion Summary")
print("-----------------")

print(
    "Accepted transactions: "
    f"{result.accepted_count}"
)

print(
    "Rejected transactions: "
    f"{result.rejected_count}"
)

print(
    "Duplicate transactions: "
    f"{result.duplicate_count}"
)

print(
    "Total amount: "
    f"{result.total_amount}"
)

print(
    "Transaction types: "
    f"{result.transaction_type_counts}"
)

print(
    "Fraud transactions: "
    f"{result.fraud_count}"
)

print(
    "Fraud amount: "
    f"{result.fraud_amount}"
)

print(
    "Fraud percentage: "
    f"{result.fraud_percentage:.2f}%"
)
