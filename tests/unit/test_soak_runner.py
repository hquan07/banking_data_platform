import argparse
from types import SimpleNamespace

import pytest

from scripts.soak.run_soak import (
    FaultSpec,
    managed_lag_expression,
    offset_total,
    parse_fault_spec,
    parse_json_lines,
    parse_topic_offsets,
    run_integrity_check,
)


def test_parses_allow_listed_fault_schedule():
    assert parse_fault_spec("spark-worker@120:20") == FaultSpec(
        name="spark-worker", at_seconds=120, outage_seconds=20,
    )
    assert parse_fault_spec("kafka@5") == FaultSpec(
        name="kafka", at_seconds=5, outage_seconds=15,
    )


@pytest.mark.parametrize("value", ["redis@1", "kafka", "neo4j@-1", "postgres@1:0"])
def test_rejects_unapproved_or_invalid_faults(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_fault_spec(value)


def test_parses_compose_json_lines_and_kafka_offsets():
    assert parse_json_lines('{"Service":"kafka"}\n{"Service":"postgres"}\n') == [
        {"Service": "kafka"}, {"Service": "postgres"},
    ]
    payment = parse_topic_offsets(
        "payment-events-dlq:0:12\npayment-events-dlq:1:8\n"
    )
    benchmark = parse_topic_offsets("benchmark-events-dlq:0:3\n")
    assert payment == {0: 12, 1: 8}
    assert offset_total({"payment": payment, "benchmark": benchmark}) == 23


def test_offset_parser_fails_closed_when_no_partition_is_observed():
    with pytest.raises(ValueError, match="no partitions"):
        parse_topic_offsets("topic output unavailable")


def test_managed_lag_excludes_legacy_benchmark_group():
    expression = managed_lag_expression()
    assert "benchmark-processor-v2" in expression
    assert "benchmark-processor-v1" not in expression
    assert "dashboard-stream-v1" in expression


def test_integrity_check_runs_reconciliation_as_module(monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(returncode=0, stdout='{"unique_payments": 0}', stderr="")

    monkeypatch.setattr("scripts.soak.run_soak.subprocess.run", fake_run)
    result = run_integrity_check()

    assert observed["command"] == [
        "docker", "compose", "--profile", "operations", "run", "--rm",
        "--no-deps", "reconciliation",
    ]
    assert result["passed"] is True
    assert result["result"]["unique_payments"] == 0
