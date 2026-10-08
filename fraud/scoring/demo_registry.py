"""Offline-only demo model selector with versioned thresholds and rollback.

The selected model is never read by the Spark fraud engine. This is an
auditable workflow demonstration, not approval for real banking inference.
"""

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REGISTRY_NAME = "demo_registry.json"


def _require_demo_mode() -> None:
    if os.environ.get("APP_MODE", "integration").lower() == "production":
        raise ValueError("demo model selection is forbidden in APP_MODE=production")


def verify_candidate(root: Path, version: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", version):
        raise ValueError("unsafe model version")
    candidate = root / version
    metadata = json.loads((candidate / "metadata.json").read_text())
    if (metadata.get("version") != version or metadata.get("data_origin") != "synthetic_demo"
            or metadata.get("production_eligible") is not False
            or metadata.get("status") != "CANDIDATE_NOT_DEPLOYED"):
        raise ValueError("only unapproved synthetic demo candidates can be selected")
    artifact_hash = hashlib.sha256((candidate / "model.joblib").read_bytes()).hexdigest()
    if artifact_hash != metadata.get("model_sha256"):
        raise ValueError("candidate model checksum mismatch")
    return metadata


def read_registry(root: Path) -> dict:
    path = root / REGISTRY_NAME
    return json.loads(path.read_text()) if path.exists() else {"scope": "synthetic_demo_only", "active": None, "history": []}


def _write_registry(root: Path, registry: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=root, prefix=".demo_registry-", delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(registry, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, root / REGISTRY_NAME)


def select_candidate(root: Path, version: str, threshold: float | None = None, action: str = "select") -> dict:
    _require_demo_mode()
    metadata = verify_candidate(root, version)
    selected_threshold = metadata["threshold"] if threshold is None else threshold
    if not isinstance(selected_threshold, (float, int)) or not 0 < selected_threshold < 1:
        raise ValueError("threshold must be between 0 and 1")
    registry = read_registry(root)
    if registry.get("scope") != "synthetic_demo_only" or not isinstance(registry.get("history"), list):
        raise ValueError("invalid demo registry")
    selection = {
        "version": version, "threshold": float(selected_threshold),
        "model_sha256": metadata["model_sha256"],
        "selected_at_utc": datetime.now(timezone.utc).isoformat(), "action": action,
    }
    registry["active"] = selection
    registry["history"].append(selection)
    _write_registry(root, registry)
    return registry


def rollback(root: Path) -> dict:
    _require_demo_mode()
    registry = read_registry(root)
    history = registry.get("history", [])
    if len(history) < 2:
        raise ValueError("no previous demo selection to roll back to")
    previous = history[-2]
    return select_candidate(root, previous["version"], previous["threshold"], action="rollback")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    select = sub.add_parser("select")
    select.add_argument("--version", required=True)
    select.add_argument("--threshold", type=float)
    sub.add_parser("rollback")
    sub.add_parser("show")
    args = parser.parse_args()
    if args.command == "select":
        result = select_candidate(args.candidates, args.version, args.threshold)
    elif args.command == "rollback":
        result = rollback(args.candidates)
    else:
        result = read_registry(args.candidates)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
