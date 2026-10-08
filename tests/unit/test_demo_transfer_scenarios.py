"""Synthetic AML fixtures must stay contract-valid and reproducible."""

from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from shared.transfer_contract import normalize_transfer_event

spec = spec_from_file_location("demo_transfer_scenarios", Path(__file__).resolve().parents[2] / "kafka/producers/demo_transfer_scenarios.py")
module = module_from_spec(spec)
spec.loader.exec_module(module)
build_all = module.build_all
build_scenario = module.build_scenario


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_all_scenarios_are_deterministic_and_contract_valid():
    events = build_all("test-run", START)
    assert events == build_all("test-run", START)
    assert len(events) == 15  # 3 + 4 + 5 + low-amount 3
    assert len({event["event_id"] for event in events}) == len(events)
    assert all(normalize_transfer_event(event) == event for event in events)
    assert all(event["data_origin"] == "synthetic_demo" for event in events)


@pytest.mark.parametrize("scenario,count", [("cycle3", 3), ("cycle4", 4), ("cycle5", 5)])
def test_cycle_scenarios_close_at_the_last_edge(scenario, count):
    events = build_scenario("test-run", scenario, START)
    assert len(events) == count
    assert events[-1]["to_account_id"] == events[0]["from_account_id"]
    assert all(float(event["amount"]) >= 1000 for event in events)


def test_low_amount_cycle_is_negative_control():
    events = build_scenario("test-run", "low_amount", START)
    assert events[-1]["to_account_id"] == events[0]["from_account_id"]
    assert sum(float(event["amount"]) < 1000 for event in events) == 1


def test_rejects_invalid_run_id_or_naive_time():
    with pytest.raises(ValueError, match="run_id"):
        build_scenario("../escape", "cycle3", START)
    with pytest.raises(ValueError, match="timezone-aware"):
        build_scenario("safe", "cycle3", datetime(2026, 1, 1))
