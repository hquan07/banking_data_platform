#!/usr/bin/env python3
"""Create and restore-check a PostgreSQL archive without replacing live data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CONTAINER = "banking_postgres"
DEFAULT_BACKUP_DIR = Path(".runtime/backups")
SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
TABLE_COUNTS_SQL = r"""
CREATE OR REPLACE FUNCTION pg_temp.project_table_counts()
RETURNS TABLE(table_name text, row_total bigint)
LANGUAGE plpgsql AS $$
DECLARE
    item record;
BEGIN
    FOR item IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schemaname, tablename
    LOOP
        table_name := item.schemaname || '.' || item.tablename;
        EXECUTE format(
            'SELECT count(*) FROM %I.%I', item.schemaname, item.tablename
        ) INTO row_total;
        RETURN NEXT;
    END LOOP;
END
$$;
SELECT table_name || '|' || row_total FROM pg_temp.project_table_counts();
"""


def _validated_name(value: str, label: str) -> str:
    if not SAFE_NAME.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def _command_error(command: list[str], stderr: bytes | str | None) -> RuntimeError:
    detail = stderr.decode(errors="replace") if isinstance(stderr, bytes) else (stderr or "")
    return RuntimeError(f"Command failed ({' '.join(command[:3])}): {detail.strip()}")


def _run(
    command: list[str],
    *,
    input_path: Path | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    input_stream = input_path.open("rb") if input_path else None
    try:
        result = subprocess.run(
            command,
            stdin=input_stream,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE,
            check=False,
        )
    finally:
        if input_stream:
            input_stream.close()
    if result.returncode != 0:
        raise _command_error(command, result.stderr)
    return result


def _docker_shell(
    container: str,
    script: str,
    *arguments: str,
    interactive: bool = False,
) -> list[str]:
    command = ["docker", "exec"]
    if interactive:
        command.append("-i")
    return [*command, container, "sh", "-c", script, "sh", *arguments]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(container: str, backup_dir: Path, timestamp: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive = backup_dir / f"postgres_{timestamp}.dump"
    temporary = archive.with_suffix(".dump.part")
    command = _docker_shell(
        container,
        'exec pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" '
        "--format=custom --no-owner --no-privileges",
    )
    with temporary.open("wb") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise _command_error(command, result.stderr)
    if temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("PostgreSQL backup is empty")
    temporary.replace(archive)
    return archive


def inspect_archive(container: str, archive: Path) -> int:
    result = _run(
        _docker_shell(container, "exec pg_restore --list", interactive=True),
        input_path=archive,
    )
    entries = [
        line
        for line in result.stdout.decode(errors="replace").splitlines()
        if line and not line.startswith(";")
    ]
    if not entries:
        raise RuntimeError("PostgreSQL archive contains no restore entries")
    return len(entries)


def parse_table_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        name, separator, value = line.rpartition("|")
        if not separator or not name:
            raise ValueError(f"Unexpected table-count row: {line!r}")
        counts[name] = int(value)
    if not counts:
        raise ValueError("No project tables were found")
    return counts


def table_counts(container: str, database: str | None = None) -> dict[str, int]:
    if database is None:
        command = _docker_shell(
            container,
            'exec psql -v ON_ERROR_STOP=1 -qAt -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB" -c "$1"',
            TABLE_COUNTS_SQL,
        )
    else:
        command = _docker_shell(
            container,
            'exec psql -v ON_ERROR_STOP=1 -qAt -U "$POSTGRES_USER" '
            '-d "$1" -c "$2"',
            database,
            TABLE_COUNTS_SQL,
        )
    output = _run(command).stdout.decode(errors="replace")
    return parse_table_counts(output)


def compare_counts(source: dict[str, int], restored: dict[str, int]) -> list[dict]:
    differences = []
    for table in sorted(source.keys() | restored.keys()):
        source_count = source.get(table)
        restored_count = restored.get(table)
        if source_count != restored_count:
            differences.append(
                {"table": table, "source": source_count, "restored": restored_count}
            )
    return differences


def rehearse_restore(container: str, archive: Path, database: str) -> tuple[dict, dict]:
    create = _docker_shell(
        container,
        'exec createdb -U "$POSTGRES_USER" "$1"',
        database,
    )
    drop = _docker_shell(
        container,
        'exec dropdb -U "$POSTGRES_USER" --if-exists --force "$1"',
        database,
    )
    _run(drop)
    _run(create)
    try:
        _run(
            _docker_shell(
                container,
                'exec pg_restore --exit-on-error --no-owner --no-privileges '
                '-U "$POSTGRES_USER" -d "$1"',
                database,
                interactive=True,
            ),
            input_path=archive,
        )
        return table_counts(container), table_counts(container, database)
    finally:
        _run(drop)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="rehearse an existing custom dump")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--report", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    container = _validated_name(args.container, "container name")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    database = _validated_name(
        f"banking_restore_rehearsal_{timestamp.lower()}_{os.getpid()}",
        "rehearsal database name",
    )
    started = time.monotonic()
    archive = args.archive or create_backup(container, args.backup_dir, timestamp)
    archive = archive.resolve()
    if not archive.is_file() or archive.stat().st_size == 0:
        raise FileNotFoundError(f"Archive is missing or empty: {archive}")

    restore_entries = inspect_archive(container, archive)
    source_counts, restored_counts = rehearse_restore(container, archive, database)
    differences = compare_counts(source_counts, restored_counts)
    report = {
        "status": "PASS" if not differences else "FAIL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "container": container,
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": _sha256(archive),
        "restore_entries": restore_entries,
        "tables_checked": len(source_counts),
        "source_rows": sum(source_counts.values()),
        "restored_rows": sum(restored_counts.values()),
        "differences": differences,
        "temporary_database_removed": True,
    }
    report_path = args.report or args.backup_dir / f"postgres_{timestamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if differences:
        raise RuntimeError(f"Restore count mismatch; see {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
