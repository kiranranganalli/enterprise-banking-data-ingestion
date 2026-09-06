from typing import Any

from pydantic import BaseModel


class APIPage(BaseModel):
    transactions: list[dict[str, Any]]
    next_page: int | None = None