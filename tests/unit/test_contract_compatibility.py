import json

from scripts.contracts.check_compatibility import breaking_changes, compare_paths


def test_additive_optional_property_is_compatible():
    baseline = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    candidate = {
        "type": "object",
        "properties": {"id": {"type": "string"}, "note": {"type": "string"}},
        "required": ["id"],
    }
    assert breaking_changes(baseline, candidate) == []


def test_new_required_property_and_narrowed_enum_are_breaking():
    baseline = {
        "type": "object", "required": ["status"],
        "properties": {"status": {"enum": ["OPEN", "CLOSED"]}},
    }
    candidate = {
        "type": "object", "required": ["status", "owner"],
        "properties": {"status": {"enum": ["OPEN"]}, "owner": {"type": "string"}},
    }
    failures = breaking_changes(baseline, candidate)
    assert any("newly required" in item for item in failures)
    assert any("enum values were removed" in item for item in failures)


def test_directory_comparison_reports_removed_schema(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    (baseline / "event.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
    assert compare_paths(baseline, candidate) == {"event.json": ["schema was removed"]}
