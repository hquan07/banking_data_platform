#!/usr/bin/env python3
"""Reject backward-incompatible JSON Schema changes within one contract version."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LOWER_BOUNDS = ("minimum", "exclusiveMinimum", "minLength", "minItems", "minProperties")
UPPER_BOUNDS = ("maximum", "exclusiveMaximum", "maxLength", "maxItems", "maxProperties")


def _types(schema: dict[str, Any]) -> set[str] | None:
    value = schema.get("type")
    if value is None:
        return None
    return {value} if isinstance(value, str) else set(value)


def breaking_changes(
    baseline: dict[str, Any], candidate: dict[str, Any], path: str = "$",
) -> list[str]:
    """Return conservative compatibility failures for accepted v1 payloads."""
    failures: list[str] = []
    old_types, new_types = _types(baseline), _types(candidate)
    if old_types is not None and new_types is not None and not old_types <= new_types:
        failures.append(f"{path}: type narrowed from {sorted(old_types)} to {sorted(new_types)}")

    if "const" in baseline and candidate.get("const") != baseline["const"]:
        failures.append(f"{path}: const changed")
    if "enum" in baseline:
        old_enum = {json.dumps(item, sort_keys=True) for item in baseline["enum"]}
        new_enum = {json.dumps(item, sort_keys=True) for item in candidate.get("enum", [])}
        if not old_enum <= new_enum:
            failures.append(f"{path}: enum values were removed")

    old_required = set(baseline.get("required", []))
    new_required = set(candidate.get("required", []))
    for field in sorted(new_required - old_required):
        failures.append(f"{path}: newly required property {field!r}")

    if baseline.get("additionalProperties", True) is not False and candidate.get("additionalProperties", True) is False:
        failures.append(f"{path}: additionalProperties changed to false")

    for keyword in LOWER_BOUNDS:
        if keyword in candidate and (
            keyword not in baseline or candidate[keyword] > baseline[keyword]
        ):
            failures.append(f"{path}: {keyword} became stricter")
    for keyword in UPPER_BOUNDS:
        if keyword in candidate and (
            keyword not in baseline or candidate[keyword] < baseline[keyword]
        ):
            failures.append(f"{path}: {keyword} became stricter")
    if "pattern" in candidate and candidate.get("pattern") != baseline.get("pattern"):
        failures.append(f"{path}: pattern changed")

    old_properties = baseline.get("properties", {})
    new_properties = candidate.get("properties", {})
    if candidate.get("additionalProperties", True) is False:
        for field in sorted(set(old_properties) - set(new_properties)):
            failures.append(f"{path}: property {field!r} is no longer accepted")
    for field in sorted(set(old_properties) & set(new_properties)):
        failures.extend(breaking_changes(
            old_properties[field], new_properties[field], f"{path}.{field}",
        ))
    return failures


def _schema_files(path: Path) -> dict[str, Path]:
    if path.is_file():
        return {path.name: path}
    return {item.relative_to(path).as_posix(): item for item in sorted(path.rglob("*.json"))}


def compare_paths(baseline_path: Path, candidate_path: Path) -> dict[str, list[str]]:
    baseline_files = _schema_files(baseline_path)
    candidate_files = _schema_files(candidate_path)
    result: dict[str, list[str]] = {}
    for name, old_path in baseline_files.items():
        new_path = candidate_files.get(name)
        if new_path is None:
            result[name] = ["schema was removed"]
            continue
        baseline = json.loads(old_path.read_text(encoding="utf-8"))
        candidate = json.loads(new_path.read_text(encoding="utf-8"))
        failures = breaking_changes(baseline, candidate)
        if failures:
            result[name] = failures
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    failures = compare_paths(args.baseline, args.candidate)
    print(json.dumps({"compatible": not failures, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
