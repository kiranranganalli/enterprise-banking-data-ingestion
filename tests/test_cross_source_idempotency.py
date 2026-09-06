from app.idempotency import ProcessedTransactionStore
from app.ingestion.csv_adapter import CSVSourceAdapter
from app.services.ingestion_service import IngestionService


def test_same_transaction_id_from_different_sources_is_not_duplicate(
    tmp_path,
):
    source_a_file = tmp_path / "bank_a.csv"
    source_b_file = tmp_path / "bank_b.csv"

    rejected_a = tmp_path / "rejected_a.jsonl"
    rejected_b = tmp_path / "rejected_b.jsonl"

    processed_file = tmp_path / "processed_ids.txt"

    source_a_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "12345,1,TRANSFER,100.00,A100,A200,0\n"
    )

    source_b_file.write_text(
        "Unnamed: 0,step,type,amount,nameOrig,nameDest,isFraud\n"
        "12345,1,TRANSFER,900.00,B100,B200,0\n"
    )

    processed_store = ProcessedTransactionStore(
        file_path=str(processed_file)
    )

    # ------------------------------------------
    # Bank A
    # ------------------------------------------

    service_a = IngestionService(
        adapter=CSVSourceAdapter(
            file_path=str(source_a_file),
            source_system="BANK_A",
        ),
        rejected_file_path=str(rejected_a),
        processed_store=processed_store,
        batch_size=1,
    )

    result_a = service_a.ingest()

    assert result_a.accepted_count == 1
    assert result_a.duplicate_count == 0

    # ------------------------------------------
    # Bank B
    # ------------------------------------------

    service_b = IngestionService(
        adapter=CSVSourceAdapter(
            file_path=str(source_b_file),
            source_system="BANK_B",
        ),
        rejected_file_path=str(rejected_b),
        processed_store=processed_store,
        batch_size=1,
    )

    result_b = service_b.ingest()

    # Same local transaction_id,
    # but a different source system.
    #
    # Therefore it must NOT be treated
    # as a duplicate.

    assert result_b.accepted_count == 1
    assert result_b.duplicate_count == 0

    # ------------------------------------------
    # Verify both idempotency keys exist
    # ------------------------------------------

    assert processed_store.is_processed(
        "BANK_A:12345"
    )

    assert processed_store.is_processed(
        "BANK_B:12345"
    )