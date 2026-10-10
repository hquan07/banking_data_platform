import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/backup/rehearse_postgres_restore.py"
)
SPEC = importlib.util.spec_from_file_location("postgres_restore_rehearsal", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_table_counts():
    assert MODULE.parse_table_counts("public.alerts|12\napp.audit|5\n") == {
        "public.alerts": 12,
        "app.audit": 5,
    }


def test_parse_table_counts_fails_closed():
    with pytest.raises(ValueError, match="Unexpected table-count row"):
        MODULE.parse_table_counts("public.alerts")
    with pytest.raises(ValueError, match="No project tables"):
        MODULE.parse_table_counts("")


def test_compare_counts_reports_missing_and_changed_tables():
    differences = MODULE.compare_counts(
        {"public.alerts": 10, "public.audit": 5},
        {"public.alerts": 9, "public.events": 4},
    )
    assert differences == [
        {"table": "public.alerts", "source": 10, "restored": 9},
        {"table": "public.audit", "source": 5, "restored": None},
        {"table": "public.events", "source": None, "restored": 4},
    ]


def test_names_reject_shell_metacharacters():
    assert MODULE._validated_name("banking_postgres", "container") == "banking_postgres"
    with pytest.raises(ValueError, match="Invalid container"):
        MODULE._validated_name("banking_postgres;rm", "container")
