from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.models.adapter_record import AdapterRecord
from app.models.page_complete import PageComplete


class SourceAdapter(ABC):

    @abstractmethod
    def read_transactions(
        self,
    ) -> Iterator[AdapterRecord | PageComplete]:
        pass