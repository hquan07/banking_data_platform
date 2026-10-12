"""Versioned semantic dashboard capabilities enriched with runtime availability."""

from __future__ import annotations

from datetime import datetime, timezone


MANIFEST_VERSION = 1
SUPPORTED_MANIFEST_VERSIONS = frozenset({MANIFEST_VERSION})

TAB_DEPENDENCIES = {
    "overview": ("postgres", "kafka", "spark"),
    "fraud": ("postgres",),
    "security": ("postgres", "minio"),
    "analytics": ("neo4j",),
    "datasets": ("postgres",),
    "history": ("postgres", "clickhouse"),
}
ALL_DEPENDENCIES = (
    "postgres", "kafka", "redis", "neo4j", "clickhouse", "minio", "spark",
    "live_ingestion",
)

DATASET_CAPABILITIES = (
    {
        "dataset_id": "live", "label": "Live", "source_kind": "live_source",
        "time_semantics": "event timestamp", "allowed_modes": ["operational"],
        "ground_truth_available": False, "graph_support": False, "case_support": False,
        "supported_tabs": ["overview", "fraud", "datasets"],
    },
    {
        "dataset_id": "ds1_creditcard", "label": "DS1 — Card Fraud",
        "source_kind": "anonymized_real",
        "time_semantics": "relative seconds from first observation",
        "allowed_modes": ["benchmark"], "ground_truth_available": True,
        "graph_support": False, "case_support": False,
        "supported_tabs": ["overview", "fraud", "datasets", "history"],
    },
    {
        "dataset_id": "ds3_paysim", "label": "DS3 — PaySim",
        "source_kind": "synthetic_simulation", "time_semantics": "simulated hourly step",
        "allowed_modes": ["benchmark"], "ground_truth_available": True,
        "graph_support": True, "case_support": True,
        "supported_tabs": ["overview", "fraud", "security", "analytics", "datasets", "history"],
    },
    {
        "dataset_id": "ds4_baf", "label": "DS4 — Account Opening Fraud",
        "source_kind": "privacy_preserving_synthetic", "time_semantics": "benchmark month 0–7",
        "allowed_modes": ["benchmark"], "ground_truth_available": True,
        "graph_support": False, "case_support": False,
        "supported_tabs": ["overview", "fraud", "datasets", "history"],
    },
)


class UnsupportedManifestVersion(ValueError):
    pass


def build_capability_manifest(readiness: dict, *, version: int = MANIFEST_VERSION, now=None) -> dict:
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        raise UnsupportedManifestVersion(version)
    now = now or datetime.now(timezone.utc)
    dependencies = {
        dependency: {
            "status": "ready" if readiness.get(dependency) is True else "failed",
            "available": readiness.get(dependency) is True,
        }
        for dependency in ALL_DEPENDENCIES
    }
    datasets = []
    for declared in DATASET_CAPABILITIES:
        supported_tabs = set(declared["supported_tabs"])
        tab_availability = {}
        for tab_id, base_required in TAB_DEPENDENCIES.items():
            required = list(base_required)
            if declared["dataset_id"] == "live" and tab_id in {"overview", "fraud"}:
                required.extend(["live_ingestion"])
            if declared["dataset_id"] == "live" and tab_id == "overview":
                required.extend(["redis"])
            required = tuple(dict.fromkeys(required))
            supported = tab_id in supported_tabs
            missing = [dependency for dependency in required if readiness.get(dependency) is not True]
            available = supported and not missing
            if not supported and tab_id in {"security", "analytics"}:
                reason = "DS3 PaySim only"
            elif not supported:
                reason = "Unsupported by dataset semantics"
            elif missing:
                reason = f"Unavailable dependencies: {', '.join(missing)}"
            else:
                reason = None
            tab_availability[tab_id] = {
                "supported": supported,
                "available": available,
                "required_dependencies": list(required),
                "missing_dependencies": missing,
                "reason": reason,
            }
        datasets.append({**declared, "tab_availability": tab_availability})
    return {
        "manifest_version": version,
        "observed_at": now.isoformat(),
        "runtime_status": readiness.get("status", "not_ready"),
        "dependencies": dependencies,
        "datasets": datasets,
    }
