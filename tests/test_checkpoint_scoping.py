from app.checkpoint import CheckpointStore


def test_checkpoints_are_scoped_by_source(tmp_path):
    base_path = tmp_path / "api_checkpoint.json"

    bank_a_store = CheckpointStore(
        file_path=str(base_path),
        source_system="BANK_A",
    )

    bank_b_store = CheckpointStore(
        file_path=str(base_path),
        source_system="BANK_B",
    )

    bank_a_store.save_next_page(5)
    bank_b_store.save_next_page(12)

    assert bank_a_store.load_next_page() == 5
    assert bank_b_store.load_next_page() == 12

    assert bank_a_store.file_path != bank_b_store.file_path
    assert bank_a_store.file_path.name == "api_checkpoint_bank_a.json"
    assert bank_b_store.file_path.name == "api_checkpoint_bank_b.json"
