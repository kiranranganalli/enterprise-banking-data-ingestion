from app.checkpoint import CheckpointStore
from app.ingestion.api_adapter import (
    APISourceAdapter,
)
from app.ingestion.base import SourceAdapter
from app.ingestion.csv_adapter import (
    CSVSourceAdapter,
)
from app.ingestion.json_adapter import (
    JSONSourceAdapter,
)


def create_source_adapter(
    source_type: str,
    file_path: str,
    api_url: str,
    checkpoint_store: CheckpointStore | None = None,
    source_system: str | None = None,
    api_token: str | None = None,
) -> SourceAdapter:
    source_type = source_type.lower()

    if source_type == "csv":
        return CSVSourceAdapter(
            file_path=file_path,
            source_system=(
                source_system or "PAYSIM"
            ),
        )

    if source_type == "json":
        return JSONSourceAdapter(
            file_path=file_path,
            source_system=(
                source_system
                or "PARTNER_JSON"
            ),
        )

    if source_type == "api":
        return APISourceAdapter(
            url=api_url,
            checkpoint_store=checkpoint_store,
            source_system=(
                source_system
                or "PARTNER_API"
            ),
            api_token=api_token,
        )

    raise ValueError(
        f"Unsupported source type: {source_type}"
    )
