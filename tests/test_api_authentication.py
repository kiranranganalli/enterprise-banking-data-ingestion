import httpx

from app.ingestion.api_adapter import (
    APISourceAdapter,
)


def test_api_sends_bearer_token(
    monkeypatch,
):
    captured_headers = {}

    def fake_get(
        url,
        params=None,
        timeout=None,
        headers=None,
    ):
        captured_headers.update(
            headers or {}
        )

        request = httpx.Request(
            "GET",
            url,
        )

        return httpx.Response(
            status_code=200,
            json=[],
            request=request,
        )

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    adapter = APISourceAdapter(
        url="https://example.com/api",
        api_token="test-secret-token",
    )

    adapter._request()

    assert (
        captured_headers[
            "Authorization"
        ]
        == "Bearer test-secret-token"
    )
