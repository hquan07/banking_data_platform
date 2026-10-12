from datetime import datetime, timezone

import pytest

from dashboard.backend.services.capabilities import (
    UnsupportedManifestVersion,
    build_capability_manifest,
)


READY = {
    "status": "ready", "postgres": True, "kafka": True, "redis": True,
    "neo4j": True, "clickhouse": True, "minio": True, "spark": True,
    "live_ingestion": True,
}


def manifest(readiness=None):
    return build_capability_manifest(
        readiness or READY, now=datetime(2026, 10, 12, tzinfo=timezone.utc),
    )


def test_manifest_schema_and_dataset_contracts_are_versioned():
    payload = manifest()
    assert payload["manifest_version"] == 1
    assert payload["observed_at"] == "2026-10-12T00:00:00+00:00"
    assert payload["runtime_status"] == "ready"
    assert set(payload["dependencies"]) == {
        "postgres", "kafka", "redis", "neo4j", "clickhouse", "minio", "spark",
        "live_ingestion",
    }
    assert {item["dataset_id"] for item in payload["datasets"]} == {
        "live", "ds1_creditcard", "ds3_paysim", "ds4_baf",
    }
    assert all(item["allowed_modes"] for item in payload["datasets"])
    assert all("tab_availability" in item for item in payload["datasets"])


def test_investigations_and_aml_are_semantically_ds3_only():
    datasets = {item["dataset_id"]: item for item in manifest()["datasets"]}
    for dataset_id, item in datasets.items():
        expected = dataset_id == "ds3_paysim"
        assert item["case_support"] is expected
        assert item["graph_support"] is expected
        assert item["tab_availability"]["security"]["supported"] is expected
        assert item["tab_availability"]["analytics"]["supported"] is expected
        if not expected:
            assert item["tab_availability"]["security"]["reason"] == "DS3 PaySim only"


def test_runtime_failure_changes_availability_not_semantic_support():
    readiness = {**READY, "status": "not_ready", "neo4j": False}
    datasets = {item["dataset_id"]: item for item in manifest(readiness)["datasets"]}
    aml = datasets["ds3_paysim"]["tab_availability"]["analytics"]
    assert aml["supported"] is True
    assert aml["available"] is False
    assert aml["missing_dependencies"] == ["neo4j"]
    assert datasets["ds3_paysim"]["tab_availability"]["security"]["available"] is True


def test_live_tabs_include_live_gateway_runtime_dependency():
    readiness = {**READY, "status": "not_ready", "live_ingestion": False}
    live = {item["dataset_id"]: item for item in manifest(readiness)["datasets"]}["live"]
    assert live["tab_availability"]["overview"]["supported"] is True
    assert live["tab_availability"]["overview"]["available"] is False
    assert "live_ingestion" in live["tab_availability"]["overview"]["missing_dependencies"]


def test_unknown_manifest_version_is_rejected():
    with pytest.raises(UnsupportedManifestVersion):
        build_capability_manifest(READY, version=999)
