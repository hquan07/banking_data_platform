#!/usr/bin/env python3
"""Apply dashboard migrations with the dedicated PostgreSQL identity."""

import os

import psycopg2

from core.migrations import apply_migrations
from shared.runtime_secrets import get_secret


def main() -> int:
    connection = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "banking_postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=get_secret("POSTGRES_PASSWORD", required=True),
    )
    connection.autocommit = True
    try:
        applied = apply_migrations(connection)
    finally:
        connection.close()
    print(f"Applied {len(applied)} migrations with dedicated identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

