"""Destructive-to-temporary-target recovery checks for the live Compose stack."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_RECOVERY_E2E") != "1",
    reason="requires the live Compose stack and explicit recovery opt-in",
)
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/backup/rehearse_multistore_restore.py"
STORES = (
    "kafka",
    "postgresql",
    "minio",
    "clickhouse",
    "neo4j",
    "spark-checkpoints",
)


def _run(report_dir: Path, *arguments: str) -> dict:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            *arguments,
            "--report-dir",
            str(report_dir),
        ],
        cwd=ROOT,
        check=True,
        timeout=1800,
    )
    reports = sorted(report_dir.glob("recovery_*/report.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text())


@pytest.mark.parametrize("store", STORES)
def test_isolated_store_restore(store: str, tmp_path: Path):
    report = _run(tmp_path, "--stores", store, "--skip-reconciliation")
    assert report["status"] == "PASS"
    assert report["stages"] == [
        {
            "duration_seconds": report["stages"][0]["duration_seconds"],
            "error": None,
            "status": "PASS",
            "store": store,
        }
    ]


def test_ordered_multistore_restore_and_reconciliation(tmp_path: Path):
    report = _run(tmp_path)
    assert report["status"] == "PASS"
    assert [stage["store"] for stage in report["stages"]] == [
        *STORES,
        "reconciliation",
    ]
    assert all(stage["status"] == "PASS" for stage in report["stages"])
