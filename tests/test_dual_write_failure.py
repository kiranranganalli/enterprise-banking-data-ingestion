import sqlite3

import pytest

from app.idempotency import ProcessedTransactionStore
from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService
from app.sqlite_sink import SQLiteTransactionSink


class CrashBeforeMarkStore:

    def __init__(
        self,
        real_store,
    ):
        self.real_store = real_store

    def is_processed(
        self,
        transaction_id,
    ):
        return self.real_store.is_processed(
            transaction_id
        )

    def mark_processed(
        self,
        transaction_id,
    ):
        raise RuntimeError(
            "Application crashed before idempotency mark"
        )

    def get_processed_ids(
        self,
        transaction_ids,
    ):
        return self.real_store.get_processed_ids(
            transaction_ids
        )

    def mark_processed_batch(
        self,
        transaction_ids,
    ):
        raise RuntimeError(
            "Application crashed before idempotency mark"
        )


def test_restart_recovers_when_sink_succeeded_before_idempotency_mark(
    tmp_path,
):
    input_file = tmp_path / "transactions.csv"
    rejected_file = tmp_path / "rejected.jsonl"

    transaction_database = (
        tmp_path / "transactions.db"
    )

    processed_file = (
        tmp_path / "processed_ids.txt"
    )

    input_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "9001,1,TRANSFER,500.00,C100,C200,0\n"
    )

    # ------------------------------------------------
    # First run
    # ------------------------------------------------

    real_processed_store = (
        ProcessedTransactionStore(
            file_path=str(processed_file)
        )
    )

    crashing_processed_store = (
        CrashBeforeMarkStore(
            real_store=real_processed_store
        )
    )

    sink = SQLiteTransactionSink(
        database_path=str(
            transaction_database
        )
    )

    first_adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    first_service = IngestionService(
        adapter=first_adapter,
        rejected_file_path=str(
            rejected_file
        ),
        processed_store=crashing_processed_store,
        sink=sink,
        batch_size=1,
    )

    # Sink succeeds, then simulated crash happens
    # during idempotency marking.
    with pytest.raises(
        RuntimeError,
        match=(
            "Application crashed before "
            "idempotency mark"
        ),
    ):
        first_service.ingest()

    # ------------------------------------------------
    # Transaction reached the sink
    # ------------------------------------------------

    with sqlite3.connect(
        transaction_database
    ) as connection:

        rows = connection.execute(
            """
            SELECT transaction_id
            FROM transactions
            """
        ).fetchall()

    assert rows == [
        ("9001",)
    ]

    # ------------------------------------------------
    # But idempotency marker was never written
    # ------------------------------------------------

    assert (
        real_processed_store.is_processed(
          "PAYSIM:9001"
        )
        is False
    )

    # ------------------------------------------------
    # Restart
    # ------------------------------------------------

    second_adapter = CSVSourceAdapter(
        file_path=str(input_file)
    )

    second_service = IngestionService(
        adapter=second_adapter,
        rejected_file_path=str(
            rejected_file
        ),
        processed_store=real_processed_store,
        sink=sink,
        batch_size=1,
    )

    # This should NOT crash anymore.
    second_result = second_service.ingest()

    assert second_result.accepted_count == 0

    assert second_result.duplicate_count == 1

    assert second_result.total_amount == 0

    # ------------------------------------------------
    # Idempotency marker gets repaired
    # ------------------------------------------------

    assert (
        real_processed_store.is_processed(
            "PAYSIM:9001"
        )
        is True
    )

    # ------------------------------------------------
    # Still only one physical transaction in sink
    # ------------------------------------------------

    with sqlite3.connect(
        transaction_database
    ) as connection:

        rows = connection.execute(
            """
            SELECT transaction_id
            FROM transactions
            """
        ).fetchall()

    assert rows == [
        ("9001",)
    ]