import json
import re
from pathlib import Path


class CheckpointStore:
    def __init__(
        self,
        file_path: str,
        source_system: str | None = None,
    ):
        base_path = Path(file_path)

        if source_system:
            safe_source = re.sub(
                r"[^a-zA-Z0-9_-]+",
                "_",
                source_system.strip(),
            ).lower()

            self.file_path = base_path.with_name(
                f"{base_path.stem}_{safe_source}{base_path.suffix}"
            )
        else:
            self.file_path = base_path

    def load_next_page(self) -> int | None:
        if not self.file_path.exists():
            return 1

        with open(self.file_path, "r") as file:
            data = json.load(file)

        return data.get("next_page", 1)

    def save_next_page(self, next_page: int | None) -> None:
        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(self.file_path, "w") as file:
            json.dump(
                {"next_page": next_page},
                file,
            )
