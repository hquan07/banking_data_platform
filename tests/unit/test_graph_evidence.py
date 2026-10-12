import pytest

from dashboard.backend.services.graph_evidence import (
    path_evidence_payload,
    temporal_path_query,
    validate_temporal_bounds,
)


def test_temporal_bounds_are_complete_ordered_and_bounded():
    assert validate_temporal_bounds(None, None) == (None, None)
    assert validate_temporal_bounds(10, 24) == (10, 24)
    for bounds in ((1, None), (None, 1), (4, 3), (0, 169), (-1, 2)):
        with pytest.raises(ValueError):
            validate_temporal_bounds(*bounds)


def test_temporal_query_bounds_hops_and_keeps_run_scope():
    query = temporal_path_query(3, anchor_by_event=True)
    assert "*1..3" in query
    assert "edge.run_id = $run_id" in query
    assert "anchor.event_id = $event_id" in query
    with pytest.raises(ValueError):
        temporal_path_query(4, anchor_by_event=False)


def test_path_payload_retains_temporal_provenance_and_identity():
    rows = [{
        "path_event_ids": ["event-1"], "path_length": 1, "hop_index": 0,
        "source_id": "run:ds3:C1", "source_display_id": "C1",
        "target_id": "run:ds3:C2", "target_display_id": "C2",
        "event_id": "event-1", "trace_id": "trace-1", "run_id": "run",
        "dataset_id": "ds3_paysim", "transaction_type": "TRANSFER", "amount": 5000,
        "relative_step": 7, "relative_time_unit": "hours", "source_row_number": 10,
        "source_file": "paysim.csv", "source_kind": "synthetic_simulation",
        "risk_score": 75, "triggered_rules": ["BALANCE_MISMATCH"],
        "evaluator_version": "benchmark-rules-v2", "processed_at": "2026-10-12T00:00:00Z",
    }]
    path = path_evidence_payload(rows)[0]
    assert path["evidence_basis"] == "participant_path"
    assert path["participant_linked"] is True
    assert path["nodes"][0]["id"].startswith("run:ds3:")
    assert path["edges"][0]["source_row_number"] == 10
    assert path["edges"][0]["risk_score"] == 75.0
    assert path["edges"][0]["source_kind"] == "synthetic_simulation"
