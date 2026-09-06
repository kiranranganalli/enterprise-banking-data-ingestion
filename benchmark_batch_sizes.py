import time
from pathlib import Path

from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService
from app.sqlite_sink import SQLiteTransactionSink


BATCH_SIZES = [
    1,
    100,
    500,
    1000,
]

INPUT_FILE = "data/transactions_100k.csv"


def run_benchmark(
    batch_size: int,
) -> None:

    database_path = Path(
        f"data/benchmark/transactions_batch_{batch_size}.db"
    )

    rejected_path = Path(
        f"data/benchmark/rejected_batch_{batch_size}.jsonl"
    )

    # Start every benchmark with a clean destination.
    if database_path.exists():
        database_path.unlink()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    adapter = CSVSourceAdapter(
        file_path=INPUT_FILE
    )

    sink = SQLiteTransactionSink(
        database_path=str(database_path)
    )

    service = IngestionService(
        adapter=adapter,
        rejected_file_path=str(rejected_path),

        # Deliberately disabled for this benchmark.
        processed_store=None,

        sink=sink,
        batch_size=batch_size,
    )

    start = time.perf_counter()

    result = service.ingest()

    duration = (
        time.perf_counter()
        - start
    )

    records = (
        result.accepted_count
        + result.rejected_count
        + result.duplicate_count
    )

    throughput = (
        records / duration
        if duration > 0
        else 0
    )

    print()
    print(
        f"Batch size: {batch_size}"
    )

    print(
        f"Duration: {duration:.4f} seconds"
    )

    print(
        f"Records: {records}"
    )

    print(
        f"Accepted: {result.accepted_count}"
    )

    print(
        f"Rejected: {result.rejected_count}"
    )

    print(
        f"Throughput: {throughput:.2f} records/sec"
    )

    print(
        "-" * 50
    )


def main() -> None:

    for batch_size in BATCH_SIZES:
        run_benchmark(
            batch_size=batch_size
        )


if __name__ == "__main__":
    main()