"""Least-privilege checks for ClickHouse runtime identities."""

from __future__ import annotations

import os
import base64
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SECURE_E2E") != "1",
    reason="requires the secure Compose overlay",
)
ROOT = Path(__file__).resolve().parents[2]
SECRET_DIR = ROOT / ".runtime/secrets"
DATABASE = os.environ["CLICKHOUSE_DB"]


def _query(user: str, secret: str, sql: str, database: str = DATABASE) -> str:
    password = (SECRET_DIR / secret).read_text().strip()
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    request = Request(
        f"http://127.0.0.1:8123/?database={database}",
        data=sql.encode(),
        headers={"Authorization": f"Basic {token}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.read().decode().strip()
    except HTTPError as exc:
        raise RuntimeError(exc.read().decode()) from exc


def test_api_is_read_only():
    assert int(_query("banking_ch_api", "clickhouse_api_password", "SELECT count() FROM payment_events")) >= 0
    with pytest.raises(RuntimeError, match="ACCESS_DENIED"):
        _query("banking_ch_api", "clickhouse_api_password", "INSERT INTO payment_events (payment_id) VALUES ('forbidden')")


def test_processor_can_insert_but_cannot_create():
    _query("banking_ch_processor", "clickhouse_processor_password", "INSERT INTO payment_events (payment_id) SELECT 'permission-probe' WHERE 0")
    with pytest.raises(RuntimeError, match="ACCESS_DENIED"):
        _query("banking_ch_processor", "clickhouse_processor_password", "CREATE TABLE forbidden_processor (id UInt8) ENGINE=Memory")


def test_migration_can_manage_application_schema():
    _query("banking_ch_migration", "clickhouse_migration_password", "CREATE TABLE IF NOT EXISTS identity_migration_probe (id UInt8) ENGINE=Memory")
    _query("banking_ch_migration", "clickhouse_migration_password", "DROP TABLE identity_migration_probe")


def test_monitor_can_read_system_but_not_application_data():
    assert int(_query("banking_ch_monitor", "clickhouse_monitor_password", "SELECT count() FROM system.tables", "system")) > 0
    with pytest.raises(RuntimeError, match="ACCESS_DENIED"):
        _query("banking_ch_monitor", "clickhouse_monitor_password", f"SELECT count() FROM {DATABASE}.payment_events", "system")


def test_backup_can_restore_to_isolated_database():
    try:
        _query("banking_ch_backup", "clickhouse_backup_password", "CREATE TABLE identity_backup_probe (id UInt8) ENGINE=Memory", "banking_recovery")
        _query("banking_ch_backup", "clickhouse_backup_password", "INSERT INTO identity_backup_probe VALUES (1)", "banking_recovery")
        assert _query("banking_ch_backup", "clickhouse_backup_password", "SELECT count() FROM identity_backup_probe", "banking_recovery") == "1"
    finally:
        _query("banking_ch_backup", "clickhouse_backup_password", "DROP TABLE IF EXISTS identity_backup_probe", "banking_recovery")

    with pytest.raises(RuntimeError, match="ACCESS_DENIED"):
        _query("banking_ch_backup", "clickhouse_backup_password", "CREATE DATABASE forbidden_backup_database", "default")
