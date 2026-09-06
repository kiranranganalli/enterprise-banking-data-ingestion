import json
import time
from collections.abc import Iterator

import httpx
from pydantic import ValidationError

from app.checkpoint import CheckpointStore
from app.ingestion.base import SourceAdapter
from app.models.adapter_record import AdapterRecord
from app.models.api_page import APIPage
from app.models.page_complete import PageComplete
from app.models.partner_json import PartnerJSONTransaction
from app.transformation.partner_json import (
    normalize_partner_json_transaction,
)


class APISourceAdapter(SourceAdapter):

    RETRYABLE_STATUS_CODES = {
        429,
        500,
        502,
        503,
        504,
    }

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        max_retries: int = 2,
        retry_delay: float = 0.5,
        checkpoint_store: CheckpointStore | None = None,
        source_system: str = "PARTNER_API",
    ):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.checkpoint_store = checkpoint_store
        self.source_system = source_system

    def _request(
        self,
        params: dict | None = None,
    ) -> httpx.Response:

        total_attempts = (
            self.max_retries + 1
        )

        for attempt in range(
            1,
            total_attempts + 1,
        ):

            try:

                response = httpx.get(
                    self.url,
                    params=params,
                    timeout=self.timeout,
                )

            except httpx.TimeoutException as error:

                if attempt == total_attempts:

                    raise RuntimeError(
                        (
                            "API request timed out "
                            f"after {total_attempts} attempts: "
                            f"{self.url}"
                        )
                    ) from error

                backoff_delay = (
                    self.retry_delay
                    * (2 ** (attempt - 1))
                )

                time.sleep(
                    backoff_delay
                )

                continue

            try:

                response.raise_for_status()

            except httpx.HTTPStatusError as error:

                status_code = (
                    error.response.status_code
                )

                if (
                    status_code
                    in self.RETRYABLE_STATUS_CODES
                    and attempt < total_attempts
                ):

                    retry_after = (
                        error.response.headers.get(
                            "Retry-After"
                        )
                    )

                    if (
                        status_code == 429
                        and retry_after is not None
                    ):

                        backoff_delay = float(
                            retry_after
                        )

                    else:

                        backoff_delay = (
                            self.retry_delay
                            * (2 ** (attempt - 1))
                        )

                    time.sleep(
                        backoff_delay
                    )

                    continue

                raise RuntimeError(
                    (
                        "API request failed "
                        f"status_code={status_code} "
                        f"url={self.url}"
                    )
                ) from error

            return response

        raise RuntimeError(
            f"API request failed: {self.url}"
        )

    def read_transactions(
        self,
    ) -> Iterator[
        AdapterRecord | PageComplete
    ]:

        # ------------------------------------------
        # Resume from checkpoint
        # ------------------------------------------

        if self.checkpoint_store is not None:

            current_page = (
                self.checkpoint_store.load_next_page()
            )

        else:

            current_page = 1

        # ------------------------------------------
        # Read API pages
        # ------------------------------------------

        while current_page is not None:

            response = self._request(
                params={
                    "page": current_page
                }
            )

            # --------------------------------------
            # Parse JSON
            # --------------------------------------

            try:

                payload = response.json()

            except json.JSONDecodeError as error:

                raise RuntimeError(
                    (
                        "API returned invalid JSON: "
                        f"{self.url}"
                    )
                ) from error

            # --------------------------------------
            # Support simple list APIs
            # --------------------------------------

            if isinstance(
                payload,
                list,
            ):

                records = payload
                next_page = None

            else:

                try:

                    api_page = (
                        APIPage.model_validate(
                            payload
                        )
                    )

                except ValidationError as error:

                    raise RuntimeError(
                        "API returned invalid page structure"
                    ) from error

                records = (
                    api_page.transactions
                )

                next_page = (
                    api_page.next_page
                )

            # --------------------------------------
            # Validate + normalize transactions
            # --------------------------------------

            for raw_transaction in records:

                try:

                    source_transaction = (
                        PartnerJSONTransaction.model_validate(
                            raw_transaction
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
                        raw_record=raw_transaction,
                        errors=json_safe_errors,
                    )

            # --------------------------------------
            # Signal page boundary
            # --------------------------------------
            #
            # IngestionService will flush the
            # database batch before saving the
            # checkpoint.

            yield PageComplete(
                next_page=next_page
            )

            current_page = (
                next_page
            )