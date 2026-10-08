from pathlib import Path

import pandas as pd

from datasets.audit_paysim_sequences import audit_paysim_sequences


def test_audit_distinguishes_sequence_from_participant_link(tmp_path: Path):
    path = tmp_path / "paysim.csv"
    pd.DataFrame([
        [1, "TRANSFER", 100, "A", "B", 1],
        [1, "CASH_OUT", 100, "C", "D", 1],
        [2, "TRANSFER", 200, "E", "MULE", 1],
        [2, "CASH_OUT", 200, "MULE", "EXIT", 1],
        [2, "PAYMENT", 10, "X", "SHOP", 0],
    ], columns=["step", "type", "amount", "nameOrig", "nameDest", "isFraud"]).to_csv(path, index=False)

    result = audit_paysim_sequences(path, chunk_size=2)

    assert result["total_rows"] == 5
    assert result["fraud_rows"] == 4
    assert result["adjacent_source_row_pairs"] == 2
    assert result["linked_participant_pairs"] == 1


def test_audit_rejects_invalid_chunk_size(tmp_path: Path):
    path = tmp_path / "paysim.csv"
    path.write_text("step,type,amount,nameOrig,nameDest,isFraud\n")

    try:
        audit_paysim_sequences(path, chunk_size=0)
    except ValueError as exc:
        assert str(exc) == "chunk_size must be positive"
    else:
        raise AssertionError("expected invalid chunk size to fail")
