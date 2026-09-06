from dataclasses import dataclass


@dataclass
class PageComplete:
    next_page: int | None