import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/backup/rehearse_multistore_restore.py"
)
SPEC = importlib.util.spec_from_file_location("multistore_restore_rehearsal", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_restore_order_keeps_offsets_and_checkpoints_after_state_stores():
    assert MODULE.RESTORE_ORDER == (
        "kafka",
        "postgresql",
        "minio",
        "clickhouse",
        "neo4j",
        "spark-checkpoints",
        "reconciliation",
    )


def test_manifest_digest_is_stable_across_mapping_order():
    first = {"store": "postgresql", "counts": {"events": 2, "alerts": 1}}
    second = {"counts": {"alerts": 1, "events": 2}, "store": "postgresql"}
    assert MODULE._json_digest(first) == MODULE._json_digest(second)


def test_safe_name_rejects_command_fragments():
    assert MODULE._safe_name("recovery_store-01", "store") == "recovery_store-01"
    with pytest.raises(ValueError, match="Invalid store"):
        MODULE._safe_name("store;docker rm", "store")


def test_stage_records_duration_and_status():
    result = MODULE._stage("minio", lambda: {"objects": 3})
    assert result["store"] == "minio"
    assert result["status"] == "PASS"
    assert result["objects"] == 3
    assert result["duration_seconds"] >= 0


def test_clickhouse_table_inventory_uses_json_rows():
    class Client:
        def query(self, sql):
            assert "database = 'banking_warehouse'" in sql
            return b'{"name":"dim_customer"}\n{"name":"payment_events"}\n'

    assert MODULE._clickhouse_tables(Client(), "banking_warehouse") == [
        "dim_customer",
        "payment_events",
    ]


def test_kafka_config_protocol_tuples_are_normalised():
    class Response:
        resources = [
            (0, "", 2, "payment-events", [("retention.ms", "604800000", False, 1, False, [])])
        ]

    class Admin:
        def describe_configs(self, resources):
            assert resources == ["resource"]
            return [Response()]

    assert MODULE._describe_kafka_configs(Admin(), ["resource"]) == {
        "payment-events": {"retention.ms": "604800000"}
    }
