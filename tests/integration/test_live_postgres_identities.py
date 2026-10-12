"""Least-privilege checks for the hardened PostgreSQL runtime identities."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SECURE_E2E") != "1",
    reason="requires the secure Compose overlay",
)
ROOT = Path(__file__).resolve().parents[2]
SECRET_DIR = ROOT / ".runtime/secrets"


def _connect(user, secret):
    return psycopg2.connect(
        host="localhost",
        port=5433,
        dbname=os.environ["POSTGRES_DB"],
        user=user,
        password=(SECRET_DIR / secret).read_text().strip(),
    )


@pytest.mark.parametrize(
    "user,secret",
    [
        ("banking_api", "postgres_api_password"),
        ("banking_processor", "postgres_processor_password"),
        ("banking_backup", "postgres_backup_password"),
        ("banking_monitor", "postgres_monitor_password"),
    ],
)
def test_runtime_identities_can_read_but_cannot_create_schema(user, secret):
    connection = _connect(user, secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM users")
            assert cursor.fetchone()[0] > 0
        connection.rollback()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE p2_identity_forbidden (id integer)")
        connection.rollback()
    finally:
        connection.close()


def test_backup_identity_is_read_only():
    connection = _connect("banking_backup", "postgres_backup_password")
    try:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO rules (name) VALUES ('forbidden-backup-write')")
        connection.rollback()
    finally:
        connection.close()


def test_processor_can_delete_but_api_cannot():
    processor = _connect("banking_processor", "postgres_processor_password")
    try:
        with processor.cursor() as cursor:
            cursor.execute("DELETE FROM pipeline_reconciliation_results WHERE FALSE")
        processor.rollback()
    finally:
        processor.close()

    api = _connect("banking_api", "postgres_api_password")
    try:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with api.cursor() as cursor:
                cursor.execute("DELETE FROM pipeline_reconciliation_results WHERE FALSE")
        api.rollback()
    finally:
        api.close()


def test_monitor_identity_can_read_stats_but_cannot_write():
    connection = _connect("banking_monitor", "postgres_monitor_password")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            assert cursor.fetchone()[0] > 0
        connection.rollback()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO rules (name) VALUES ('forbidden-monitor-write')")
        connection.rollback()
    finally:
        connection.close()


def test_migration_identity_can_create_and_remove_owned_objects():
    connection = _connect("banking_migration", "postgres_migration_password")
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS p2_identity_migration_probe (id integer)")
            cursor.execute("DROP TABLE p2_identity_migration_probe")
            cursor.execute(
                "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
            )
            assert cursor.fetchone() == (False,)
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cursor.execute("SET ROLE banking_user")
    finally:
        connection.close()
