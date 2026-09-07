from app.ingestion.api_adapter import APISourceAdapter
from app.ingestion.factory import create_source_adapter


def test_factory_passes_api_token_to_api_adapter():
    adapter = create_source_adapter(
        source_type="api",
        file_path="unused.json",
        api_url="https://example.com/api",
        api_token="test-secret-token",
    )

    assert isinstance(adapter, APISourceAdapter)
    assert adapter.api_token == "test-secret-token"
