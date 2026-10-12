#!/usr/bin/env python3
"""Create local Docker secret files without printing secret values."""

from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRECTORY = ROOT / ".runtime/secrets"
GENERATED = (
    "postgres_api_password",
    "postgres_processor_password",
    "postgres_migration_password",
    "postgres_backup_password",
    "postgres_monitor_password",
    "clickhouse_api_password",
    "clickhouse_processor_password",
    "clickhouse_migration_password",
    "clickhouse_backup_password",
    "clickhouse_monitor_password",
)


def _write_secret(path: Path, value: str, *, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        path.chmod(0o444)
        return False
    temporary = path.with_suffix(".part")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(descriptor, (value + "\n").encode())
    finally:
        os.close(descriptor)
    temporary.replace(path)
    # Compose bind-mounts local secrets and cannot remap their uid/gid.  The
    # parent directory is private (0700), while 0444 lets non-root container
    # users read only the individual secret explicitly mounted for them.
    path.chmod(0o444)
    return True


def bootstrap(directory: Path, env_file: Path, *, rotate: bool = False) -> list[str]:
    values = dotenv_values(env_file)
    admin_secrets = {
        "postgres_admin_password": values.get("POSTGRES_PASSWORD"),
        "clickhouse_admin_password": values.get("CLICKHOUSE_PASSWORD"),
    }
    missing = [name for name, value in admin_secrets.items() if not value]
    if missing:
        raise RuntimeError(f"Admin credentials are missing from {env_file}: {', '.join(missing)}")
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    changed = []
    for name, value in admin_secrets.items():
        if _write_secret(directory / name, str(value), overwrite=True):
            changed.append(name)
    for name in GENERATED:
        if _write_secret(
            directory / name,
            secrets.token_urlsafe(36),
            overwrite=rotate,
        ):
            changed.append(name)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="rotate dedicated runtime identities; the admin copy is always refreshed",
    )
    args = parser.parse_args()
    changed = bootstrap(args.directory.resolve(), args.env_file.resolve(), rotate=args.rotate)
    print(
        f"Local secret provider ready at {args.directory.resolve()} "
        f"({len(changed)} files written; values suppressed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
