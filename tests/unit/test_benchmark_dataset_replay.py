import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts/benchmark_dataset_replay.py"
SPEC = importlib.util.spec_from_file_location("benchmark_dataset_replay_under_test", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

latency_summary = MODULE.latency_summary
parse_consumer_group_lag = MODULE.parse_consumer_group_lag
parse_producer_summary = MODULE.parse_producer_summary
parse_topic_offsets = MODULE.parse_topic_offsets
percentile = MODULE.percentile


def test_percentiles_and_latency_summary_are_interpolated():
    assert percentile([10, 20, 30], 0.5) == 20
    assert percentile([10, 20], 0.95) == pytest.approx(19.5)
    summary = latency_summary([1.0, 2.0, 3.0, 4.0])
    assert summary["samples"] == 4
    assert summary["p50_ms"] == 2.5
    assert summary["p95_ms"] == 3.85


def test_parse_consumer_group_lag_sums_partitions():
    output = """
GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID HOST CLIENT-ID
benchmark benchmark-events 0 100 105 5 consumer /host client
benchmark benchmark-events 1 200 203 3 consumer /host client
"""
    assert parse_consumer_group_lag(output) == 8


def test_parse_offsets_and_producer_summary():
    assert parse_topic_offsets(
        "benchmark-events-dlq:0:4\nbenchmark-events-dlq:1:7\n"
    ) == {0: 4, 1: 7}
    output = "starting container\n" + json.dumps({"published": 100, "rejected": 0})
    assert parse_producer_summary(output)["published"] == 100


def test_parsers_fail_closed_on_missing_measurements():
    with pytest.raises(ValueError, match="no lag rows"):
        parse_consumer_group_lag("GROUP TOPIC PARTITION LAG")
    with pytest.raises(ValueError, match="no partitions"):
        parse_topic_offsets("not an offset")
    with pytest.raises(ValueError, match="no producer summary"):
        parse_producer_summary("not json")
