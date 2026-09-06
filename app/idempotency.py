from pathlib import Path
from typing import Protocol


class ProcessedStore(Protocol):

    def is_processed(
        self,
        transaction_id: str,
    ) -> bool:
        ...

    def mark_processed(
        self,
        transaction_id: str,
    ) -> None:
        ...

    def get_processed_ids(
        self,
        transaction_ids: list[str],
    ) -> set[str]:
        ...

    def mark_processed_batch(
        self,
        transaction_ids: list[str],
    ) -> None:
        ...


class ProcessedTransactionStore:

    def __init__(
        self,
        file_path: str,
    ):
        self.file_path = Path(file_path)

        self.processed_ids = self._load_ids()

    def _load_ids(self) -> set[str]:

        if not self.file_path.exists():
            return set()

        with open(
            self.file_path,
            "r",
        ) as file:

            return {
                line.strip()
                for line in file
                if line.strip()
            }

    def is_processed(
        self,
        transaction_id: str,
    ) -> bool:

        return (
            transaction_id
            in self.processed_ids
        )

    def mark_processed(
        self,
        transaction_id: str,
    ) -> None:

        if (
            transaction_id
            in self.processed_ids
        ):
            return

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.file_path,
            "a",
        ) as file:

            file.write(
                transaction_id + "\n"
            )

        self.processed_ids.add(
            transaction_id
        )

    def get_processed_ids(
        self,
        transaction_ids: list[str],
    ) -> set[str]:

        return {
            transaction_id
            for transaction_id in transaction_ids
            if transaction_id in self.processed_ids
        }

    def mark_processed_batch(
        self,
        transaction_ids: list[str],
    ) -> None:

        for transaction_id in transaction_ids:

            self.mark_processed(
                transaction_id
            )