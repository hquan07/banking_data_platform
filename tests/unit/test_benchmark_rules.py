from copy import deepcopy
import importlib.util
from pathlib import Path

from fraud.rules.benchmark_rules import evaluate_baf, evaluate_benchmark_payload, evaluate_paysim


PROCESSOR_PATH = Path(__file__).resolve().parents[2] / "kafka/consumers/benchmark_processor.py"
SPEC = importlib.util.spec_from_file_location("benchmark_processor_under_test", PROCESSOR_PATH)
PROCESSOR_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROCESSOR_MODULE)
build_alert = PROCESSOR_MODULE.build_alert


def test_paysim_balance_mismatch_and_zero_drain_are_source_specific():
    signals = evaluate_paysim({
        "transaction_type": "TRANSFER",
        "amount": 20_000,
        "balances": {
            "origin_before": 30_000,
            "origin_after": 0,
        },
    })
    assert [signal["rule"] for signal in signals] == ["BALANCE_MISMATCH", "ZERO_DRAIN"]


def test_paysim_does_not_flag_insufficient_balance_as_mismatch():
    assert evaluate_paysim({
        "transaction_type": "TRANSFER",
        "amount": 20_000,
        "balances": {"origin_before": 100, "origin_after": 0},
    }) == []


def test_baf_negative_missing_sentinel_is_not_short_session():
    assert evaluate_baf({"features": {
        "device_fraud_count": 0,
        "date_of_birth_distinct_emails_4w": 0,
        "session_length_in_minutes": -1,
    }}) == []


def test_ds1_and_ds2_are_not_scored_without_calibrated_model():
    assert evaluate_benchmark_payload("ds1_creditcard", {"amount": 999_999}) == []
    assert evaluate_benchmark_payload("ds2_ieee_cis", {"identity": {"id_12": "Found"}}) == []


def test_ground_truth_cannot_change_rules_or_alert_identity():
    event = {
        "event_id": "ds3_paysim:10",
        "trace_id": "ds3_paysim:10",
        "dataset_id": "ds3_paysim",
        "payload": {
            "transaction_type": "TRANSFER",
            "amount": 20_000,
            "participant_ids": {"origin": "C1", "destination": "C2"},
            "balances": {"origin_before": 30_000, "origin_after": 0},
        },
        "ground_truth": {"is_fraud": False},
    }
    changed = deepcopy(event)
    changed["ground_truth"]["is_fraud"] = True
    first = evaluate_benchmark_payload(event["dataset_id"], event["payload"])
    second = evaluate_benchmark_payload(changed["dataset_id"], changed["payload"])
    assert first == second
    alert = build_alert(event, first[0])
    assert alert["entity_id"] == "C1"
    assert alert["entity_type"] == "simulated_account"
