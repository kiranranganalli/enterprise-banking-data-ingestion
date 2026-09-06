import json
from decimal import Decimal

import httpx
import pytest

from app.ingestion.api_adapter import APISourceAdapter
from app.services.ingestion_service import IngestionService
from app.checkpoint import CheckpointStore
from app.idempotency import ProcessedTransactionStore
from app.sqlite_idempotency import SQLiteProcessedTransactionStore


class FakeResponse:

    def raise_for_status(self):
        pass

    def json(self):
        return [
            {
                "transaction_id": "API1001",
                "transaction_type": "TRANSFER",
                "transaction_amount": "750.00",
                "source_account": "C500",
                "destination_account": "C600",
                "fraud_flag": 0,
            },
            {
                "transaction_id": "API1002",
                "transaction_type": "PAYMENT",
                "transaction_amount": "125.50",
                "source_account": "C501",
                "destination_account": "M700",
                "fraud_flag": 0,
            },
            {
                "transaction_id": "API1003",
                "transaction_type": "CASH_OUT",
                "transaction_amount": "2000.00",
                "source_account": "C502",
                "destination_account": "C800",
                "fraud_flag": 1,
            },
            {
                "transaction_id": "API1004",
                "transaction_type": "TRANSFER",
                "transaction_amount": "-500.00",
                "source_account": "C900",
                "destination_account": "C901",
                "fraud_flag": 0,
            },
        ]


def test_api_ingestion_processes_valid_and_invalid_records(
    tmp_path,
    monkeypatch,
):

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions"
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert result.accepted_count == 3
    assert result.rejected_count == 1
    assert result.total_amount == Decimal("2875.50")

    assert result.transaction_type_counts == {
        "TRANSFER": 1,
        "PAYMENT": 1,
        "CASH_OUT": 1,
    }

    assert result.fraud_count == 1
    assert result.fraud_amount == Decimal("2000.00")


def test_api_timeout_raises_clear_error(
    tmp_path,
    monkeypatch,
):

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        raise httpx.TimeoutException(
            "Request timed out"
        )

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    with pytest.raises(
        RuntimeError,
        match="API request timed out",
    ):
        service.ingest()


def test_api_http_error_raises_clear_error(
    tmp_path,
    monkeypatch,
):

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    response = httpx.Response(
        500,
        request=request,
    )

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return response

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    with pytest.raises(
        RuntimeError,
        match="status_code=500",
    ):
        service.ingest()


def test_api_invalid_json_raises_clear_error(
    tmp_path,
    monkeypatch,
):

    class InvalidJSONResponse:

        def raise_for_status(self):
            pass

        def json(self):
            raise json.JSONDecodeError(
                "Invalid JSON",
                "bad-json",
                0,
            )

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return InvalidJSONResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions"
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    with pytest.raises(
        RuntimeError,
        match="API returned invalid JSON",
    ):
        service.ingest()


def test_api_retry_succeeds_after_timeout(
    tmp_path,
    monkeypatch,
):

    call_count = 0

    class SuccessfulResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "API2001",
                    "transaction_type": "TRANSFER",
                    "transaction_amount": "500.00",
                    "source_account": "C100",
                    "destination_account": "C200",
                    "fraud_flag": 0,
                }
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            raise httpx.TimeoutException(
                "Temporary timeout"
            )

        return SuccessfulResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert call_count == 2
    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("500.00")


def test_api_retry_succeeds_after_503(
    tmp_path,
    monkeypatch,
):

    call_count = 0

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    unavailable_response = httpx.Response(
        503,
        request=request,
    )

    class SuccessfulResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "API3001",
                    "transaction_type": "PAYMENT",
                    "transaction_amount": "250.00",
                    "source_account": "C300",
                    "destination_account": "M400",
                    "fraud_flag": 0,
                }
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            return unavailable_response

        return SuccessfulResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert call_count == 2
    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("250.00")


def test_api_401_does_not_retry(
    tmp_path,
    monkeypatch,
):

    call_count = 0

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    unauthorized_response = httpx.Response(
        401,
        request=request,
    )

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal call_count

        call_count += 1

        return unauthorized_response

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    with pytest.raises(
        RuntimeError,
        match="status_code=401",
    ):
        service.ingest()

    assert call_count == 1


def test_api_429_uses_retry_after_and_recovers(
    tmp_path,
    monkeypatch,
):

    call_count = 0
    sleep_calls = []

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    rate_limited_response = httpx.Response(
        429,
        headers={
            "Retry-After": "3"
        },
        request=request,
    )

    class SuccessfulResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "API4001",
                    "transaction_type": "TRANSFER",
                    "transaction_amount": "600.00",
                    "source_account": "C400",
                    "destination_account": "C500",
                    "fraud_flag": 0,
                }
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            return rate_limited_response

        return SuccessfulResponse()

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        "app.ingestion.api_adapter.time.sleep",
        fake_sleep,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert call_count == 2
    assert sleep_calls == [3.0]

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("600.00")


def test_api_pagination_reads_all_pages(
    tmp_path,
    monkeypatch,
):

    requested_pages = []

    class PageResponse:

        def __init__(
            self,
            transactions,
            next_page,
        ):
            self.transactions = transactions
            self.next_page = next_page

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transactions": self.transactions,
                "next_page": self.next_page,
            }

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):

        page = params["page"]

        requested_pages.append(page)

        if page == 1:
            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE1001",
                        "transaction_type": "TRANSFER",
                        "transaction_amount": "100.00",
                        "source_account": "C100",
                        "destination_account": "C200",
                        "fraud_flag": 0,
                    }
                ],
                next_page=2,
            )

        if page == 2:
            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE2001",
                        "transaction_type": "PAYMENT",
                        "transaction_amount": "200.00",
                        "source_account": "C300",
                        "destination_account": "M400",
                        "fraud_flag": 0,
                    }
                ],
                next_page=3,
            )

        if page == 3:
            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE3001",
                        "transaction_type": "CASH_OUT",
                        "transaction_amount": "300.00",
                        "source_account": "C500",
                        "destination_account": "C600",
                        "fraud_flag": 1,
                    }
                ],
                next_page=None,
            )

        raise AssertionError(
            f"Unexpected page requested: {page}"
        )

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert requested_pages == [
        1,
        2,
        3,
    ]

    assert result.accepted_count == 3
    assert result.rejected_count == 0

    assert result.total_amount == Decimal("600.00")

    assert result.transaction_type_counts == {
        "TRANSFER": 1,
        "PAYMENT": 1,
        "CASH_OUT": 1,
    }

    assert result.fraud_count == 1
    assert result.fraud_amount == Decimal("300.00")


def test_api_pagination_retries_failed_page(
    tmp_path,
    monkeypatch,
):

    page_2_attempts = 0
    requested_pages = []

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    unavailable_response = httpx.Response(
        503,
        request=request,
    )

    class PageResponse:

        def __init__(
            self,
            transactions,
            next_page,
        ):
            self.transactions = transactions
            self.next_page = next_page

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transactions": self.transactions,
                "next_page": self.next_page,
            }

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal page_2_attempts

        page = params["page"]

        requested_pages.append(page)

        if page == 1:
            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE1001",
                        "transaction_type": "TRANSFER",
                        "transaction_amount": "100.00",
                        "source_account": "C100",
                        "destination_account": "C200",
                        "fraud_flag": 0,
                    }
                ],
                next_page=2,
            )

        if page == 2:
            page_2_attempts += 1

            if page_2_attempts == 1:
                return unavailable_response

            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE2001",
                        "transaction_type": "PAYMENT",
                        "transaction_amount": "200.00",
                        "source_account": "C300",
                        "destination_account": "M400",
                        "fraud_flag": 0,
                    }
                ],
                next_page=3,
            )

        if page == 3:
            return PageResponse(
                transactions=[
                    {
                        "transaction_id": "PAGE3001",
                        "transaction_type": "CASH_OUT",
                        "transaction_amount": "300.00",
                        "source_account": "C500",
                        "destination_account": "C600",
                        "fraud_flag": 0,
                    }
                ],
                next_page=None,
            )

        raise AssertionError(
            f"Unexpected page requested: {page}"
        )

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert requested_pages == [
        1,
        2,
        2,
        3,
    ]

    assert page_2_attempts == 2

    assert result.accepted_count == 3
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("600.00")


def test_api_resumes_from_saved_checkpoint(
    tmp_path,
    monkeypatch,
):

    requested_pages = []

    checkpoint_file = tmp_path / "checkpoint.json"

    checkpoint_store = CheckpointStore(
        file_path=str(checkpoint_file)
    )

    # Pretend a previous run already completed
    # pages 1 and 2.
    checkpoint_store.save_next_page(3)

    class PageResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transactions": [
                    {
                        "transaction_id": "PAGE3001",
                        "transaction_type": "TRANSFER",
                        "transaction_amount": "700.00",
                        "source_account": "C700",
                        "destination_account": "C800",
                        "fraud_flag": 0,
                    }
                ],
                "next_page": None,
            }

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        requested_pages.append(
            params["page"]
        )

        return PageResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
        checkpoint_store=checkpoint_store,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert requested_pages == [3]

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("700.00")

def test_api_checkpoint_survives_crash_and_resumes(
    tmp_path,
    monkeypatch,
):

    checkpoint_file = tmp_path / "checkpoint.json"

    checkpoint_store = CheckpointStore(
        file_path=str(checkpoint_file)
    )

    first_run_pages = []

    request = httpx.Request(
        "GET",
        "https://fake-bank.test/transactions",
    )

    failed_response = httpx.Response(
        500,
        request=request,
    )

    class PageOneResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transactions": [
                    {
                        "transaction_id": "PAGE1001",
                        "transaction_type": "TRANSFER",
                        "transaction_amount": "100.00",
                        "source_account": "C100",
                        "destination_account": "C200",
                        "fraud_flag": 0,
                    }
                ],
                "next_page": 2,
            }

    def first_run_fake_get(
        url,
        params=None,
        timeout=None,
    ):
        page = params["page"]

        first_run_pages.append(page)

        if page == 1:
            return PageOneResponse()

        if page == 2:
            return failed_response

        raise AssertionError(
            f"Unexpected page: {page}"
        )

    monkeypatch.setattr(
        httpx,
        "get",
        first_run_fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    first_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        max_retries=0,
        retry_delay=0,
        checkpoint_store=checkpoint_store,
    )

    first_service = IngestionService(
        adapter=first_adapter,
        rejected_file_path=str(rejected_file),
    )

    with pytest.raises(
        RuntimeError,
        match="status_code=500",
    ):
        first_service.ingest()

    # Page 1 finished successfully.
    # Therefore page 2 should be saved.
    assert checkpoint_store.load_next_page() == 2

    assert first_run_pages == [
        1,
        2,
    ]

    # -----------------------------------------
    # Simulate application restart
    # -----------------------------------------

    second_run_pages = []

    class PageTwoResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transactions": [
                    {
                        "transaction_id": "PAGE2001",
                        "transaction_type": "PAYMENT",
                        "transaction_amount": "200.00",
                        "source_account": "C300",
                        "destination_account": "M400",
                        "fraud_flag": 0,
                    }
                ],
                "next_page": None,
            }

    def second_run_fake_get(
        url,
        params=None,
        timeout=None,
    ):
        page = params["page"]

        second_run_pages.append(page)

        return PageTwoResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        second_run_fake_get,
    )

    second_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        max_retries=0,
        retry_delay=0,
        checkpoint_store=checkpoint_store,
    )

    second_service = IngestionService(
        adapter=second_adapter,
        rejected_file_path=str(rejected_file),
    )

    result = second_service.ingest()

    assert second_run_pages == [2]

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("200.00")

def test_completed_checkpoint_makes_no_api_request(
    tmp_path,
    monkeypatch,
):

    checkpoint_file = tmp_path / "checkpoint.json"

    checkpoint_store = CheckpointStore(
        file_path=str(checkpoint_file)
    )

    # Pretend the previous ingestion finished completely.
    checkpoint_store.save_next_page(None)

    call_count = 0

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        nonlocal call_count

        call_count += 1

        raise AssertionError(
            "API should not be called after ingestion is complete"
        )

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
        checkpoint_store=checkpoint_store,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
    )

    result = service.ingest()

    assert call_count == 0

    assert result.accepted_count == 0
    assert result.rejected_count == 0
    assert result.total_amount == Decimal("0")


def test_duplicate_transaction_is_skipped(
    tmp_path,
    monkeypatch,
):

    class DuplicateResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "TX1001",
                    "transaction_type": "TRANSFER",
                    "transaction_amount": "100.00",
                    "source_account": "C100",
                    "destination_account": "C200",
                    "fraud_flag": 0,
                },
                {
                    "transaction_id": "TX1002",
                    "transaction_type": "PAYMENT",
                    "transaction_amount": "200.00",
                    "source_account": "C300",
                    "destination_account": "M400",
                    "fraud_flag": 0,
                },
                {
                    "transaction_id": "TX1002",
                    "transaction_type": "PAYMENT",
                    "transaction_amount": "200.00",
                    "source_account": "C300",
                    "destination_account": "M400",
                    "fraud_flag": 0,
                },
                {
                    "transaction_id": "TX1003",
                    "transaction_type": "CASH_OUT",
                    "transaction_amount": "300.00",
                    "source_account": "C500",
                    "destination_account": "C600",
                    "fraud_flag": 0,
                },
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return DuplicateResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"
    processed_file = tmp_path / "processed_ids.txt"

    processed_store = ProcessedTransactionStore(
        file_path=str(processed_file)
    )

    adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_file),
        processed_store=processed_store,
    )

    result = service.ingest()

    assert result.accepted_count == 3
    assert result.rejected_count == 0
    assert result.duplicate_count == 1

    assert result.total_amount == Decimal("600.00")

    assert result.transaction_type_counts == {
        "TRANSFER": 1,
        "PAYMENT": 1,
        "CASH_OUT": 1,
    }


def test_duplicate_transaction_is_skipped_after_restart(
    tmp_path,
    monkeypatch,
):

    class TransactionResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "TX5001",
                    "transaction_type": "TRANSFER",
                    "transaction_amount": "400.00",
                    "source_account": "C500",
                    "destination_account": "C600",
                    "fraud_flag": 0,
                }
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return TransactionResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"
    processed_file = tmp_path / "processed_ids.txt"

    # -----------------------------------------
    # First application run
    # -----------------------------------------

    first_store = ProcessedTransactionStore(
        file_path=str(processed_file)
    )

    first_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    first_service = IngestionService(
        adapter=first_adapter,
        rejected_file_path=str(rejected_file),
        processed_store=first_store,
    )

    first_result = first_service.ingest()

    assert first_result.accepted_count == 1
    assert first_result.duplicate_count == 0
    assert first_result.total_amount == Decimal("400.00")

    # -----------------------------------------
    # Simulate application restart
    # -----------------------------------------

    second_store = ProcessedTransactionStore(
        file_path=str(processed_file)
    )

    second_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    second_service = IngestionService(
        adapter=second_adapter,
        rejected_file_path=str(rejected_file),
        processed_store=second_store,
    )

    second_result = second_service.ingest()

    assert second_result.accepted_count == 0
    assert second_result.duplicate_count == 1
    assert second_result.total_amount == Decimal("0")

def test_sqlite_idempotency_skips_duplicate_after_restart(
    tmp_path,
    monkeypatch,
):

    class TransactionResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "transaction_id": "SQLTX1001",
                    "transaction_type": "TRANSFER",
                    "transaction_amount": "900.00",
                    "source_account": "C100",
                    "destination_account": "C200",
                    "fraud_flag": 0,
                }
            ]

    def fake_get(
        url,
        params=None,
        timeout=None,
    ):
        return TransactionResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    rejected_file = tmp_path / "rejected.jsonl"
    database_file = tmp_path / "idempotency.db"

    # -----------------------------------------
    # First application run
    # -----------------------------------------

    first_store = SQLiteProcessedTransactionStore(
        database_path=str(database_file)
    )

    first_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    first_service = IngestionService(
        adapter=first_adapter,
        rejected_file_path=str(rejected_file),
        processed_store=first_store,
    )

    first_result = first_service.ingest()

    assert first_result.accepted_count == 1
    assert first_result.duplicate_count == 0
    assert first_result.total_amount == Decimal("900.00")

    # -----------------------------------------
    # Simulate application restart
    # -----------------------------------------

    second_store = SQLiteProcessedTransactionStore(
        database_path=str(database_file)
    )

    second_adapter = APISourceAdapter(
        url="https://fake-bank.test/transactions",
        retry_delay=0,
    )

    second_service = IngestionService(
        adapter=second_adapter,
        rejected_file_path=str(rejected_file),
        processed_store=second_store,
    )

    second_result = second_service.ingest()

    assert second_result.accepted_count == 0
    assert second_result.duplicate_count == 1
    assert second_result.total_amount == Decimal("0")