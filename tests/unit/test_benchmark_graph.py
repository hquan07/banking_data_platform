from copy import deepcopy
import importlib.util
from pathlib import Path


GRAPH_PATH = Path(__file__).resolve().parents[2] / "aml/graph/benchmark_graph.py"
SPEC = importlib.util.spec_from_file_location("benchmark_graph_under_test", GRAPH_PATH)
GRAPH_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GRAPH_MODULE)
graph_record = GRAPH_MODULE.graph_record
build_sequence_alert = GRAPH_MODULE.build_sequence_alert


def _event(tx_type="TRANSFER", label=False):
    return {
        "event_id": "ds3_paysim:10",
        "trace_id": "ds3_paysim:10",
        "dataset_id": "ds3_paysim",
        "source_row_id": "10",
        "event_time": {"value": 7},
        "payload": {
            "transaction_type": tx_type,
            "amount": 5000,
            "participant_ids": {"origin": "C1", "destination": "C2"},
        },
        "ground_truth": {"is_fraud": label},
    }


def test_graph_record_uses_isolated_synthetic_account_ids():
    record = graph_record(_event())
    assert record["origin_id"] == "ds3_paysim:C1"
    assert record["destination_id"] == "ds3_paysim:C2"
    assert record["relative_step"] == 7
    assert record["source_row_number"] == 10


def test_label_change_does_not_change_sequence_alert():
    transfer = graph_record(_event("TRANSFER", False))
    cashout_event = _event("CASH_OUT", False)
    cashout_event["event_id"] = "ds3_paysim:11"
    cashout_event["trace_id"] = "ds3_paysim:11"
    cashout_event["source_row_id"] = "11"
    cashout = graph_record(cashout_event)
    changed_event = deepcopy(cashout_event)
    changed_event["ground_truth"]["is_fraud"] = True
    changed = graph_record(changed_event)
    first = build_sequence_alert(transfer, cashout)
    second = build_sequence_alert(transfer, changed)
    assert first == second
    assert first["rule"] == "TRANSFER_CASHOUT_SEQUENCE"
    assert first["entity_type"] == "benchmark_sequence"
    assert first["evidence"]["participant_linked"] is False


def test_non_paysim_event_is_not_added_to_benchmark_graph():
    event = deepcopy(_event())
    event["dataset_id"] = "ds1_creditcard"
    assert graph_record(event) is None
