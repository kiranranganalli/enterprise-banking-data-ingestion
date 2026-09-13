from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    input_file_path: str = "data/transactions.csv"

    rejected_file_path: str = (
        "data/rejected/rejected_transactions.jsonl"
    )

    source_type: str = "csv"
    source_system: str | None = None

    api_url: str = (
        "http://localhost:8000/"
        "data/api_transactions.json"
    )

    api_token: str | None = None

    checkpoint_file_path: str = (
        "data/state/api_checkpoint.json"
    )

    idempotency_database_path: str = (
        "data/state/idempotency.db"
    )

    transaction_database_path: str = (
        "data/output/transactions.db"
    )

    database_backend: str = "sqlite"
    database_url: str | None = None

    batch_size: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
