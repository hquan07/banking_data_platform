#!/usr/bin/env bash
set -euo pipefail

password=$(tr -d '\r\n' < /run/secrets/clickhouse_migration_password)
CLICKHOUSE_PASSWORD="$password" clickhouse-client \
  --host banking_clickhouse \
  --user "$CLICKHOUSE_MIGRATION_USER" \
  --database "$CLICKHOUSE_DB" \
  --multiquery < /migrations/init.sql

echo "ClickHouse migrations applied with dedicated identity."
