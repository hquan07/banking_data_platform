"""Demo registry never selects unverified or production models."""

import hashlib
import json

import pytest

from fraud.scoring.demo_registry import read_registry, rollback, select_candidate


def candidate(root, version, *, data_origin="synthetic_demo"):
    path = root / version
    path.mkdir()
    artifact = b"test-only-not-a-real-model"
    (path / "model.joblib").write_bytes(artifact)
    (path / "metadata.json").write_text(json.dumps({
        "version": version, "data_origin": data_origin, "production_eligible": False,
        "status": "CANDIDATE_NOT_DEPLOYED", "threshold": 0.7,
        "model_sha256": hashlib.sha256(artifact).hexdigest(),
    }))


def test_selection_threshold_history_and_rollback(tmp_path):
    candidate(tmp_path, "demo-v1")
    candidate(tmp_path, "demo-v2")
    select_candidate(tmp_path, "demo-v1")
    select_candidate(tmp_path, "demo-v2", 0.8)
    result = rollback(tmp_path)
    assert result["scope"] == "synthetic_demo_only"
    assert result["active"]["version"] == "demo-v1"
    assert result["active"]["threshold"] == 0.7
    assert [item["action"] for item in result["history"]] == ["select", "select", "rollback"]
    assert read_registry(tmp_path) == result


def test_rejects_real_data_tampered_artifact_and_production_mode(tmp_path, monkeypatch):
    candidate(tmp_path, "demo-v1")
    candidate(tmp_path, "not-demo", data_origin="unverified")
    with pytest.raises(ValueError, match="synthetic"):
        select_candidate(tmp_path, "not-demo")
    (tmp_path / "demo-v1/model.joblib").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        select_candidate(tmp_path, "demo-v1")
    monkeypatch.setenv("APP_MODE", "production")
    with pytest.raises(ValueError, match="forbidden"):
        select_candidate(tmp_path, "demo-v1")


def test_rejects_unsafe_version_and_no_rollback(tmp_path):
    with pytest.raises(ValueError, match="unsafe"):
        select_candidate(tmp_path, "../escape")
    with pytest.raises(ValueError, match="no previous"):
        rollback(tmp_path)
