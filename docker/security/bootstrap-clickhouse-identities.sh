#!/usr/bin/env bash
set -euo pipefail

validate_name() {
  if [[ ! "$2" =~ ^[A-Za-z_][A-Za-z0-9_]{0,63}$ ]]; then
    echo "Invalid ClickHouse $1 identity" >&2
    exit 1
  fi
}

read_secret() {
  local value
  value=$(tr -d '\r\n' < "$1")
  if [[ ! "$value" =~ ^[A-Za-z0-9_-]{32,128}$ ]]; then
    echo "Dedicated ClickHouse secret has an invalid format" >&2
    exit 1
  fi
  printf '%s' "$value"
}

validate_name admin "$CLICKHOUSE_ADMIN_USER"
validate_name api "$CLICKHOUSE_API_USER"
validate_name processor "$CLICKHOUSE_PROCESSOR_USER"
validate_name migration "$CLICKHOUSE_MIGRATION_USER"
validate_name backup "$CLICKHOUSE_BACKUP_USER"
validate_name monitor "$CLICKHOUSE_MONITOR_USER"
validate_name database "$CLICKHOUSE_DB"

admin_password=$(tr -d '\r\n' < /run/secrets/clickhouse_admin_password)
api_password=$(read_secret /run/secrets/clickhouse_api_password)
processor_password=$(read_secret /run/secrets/clickhouse_processor_password)
migration_password=$(read_secret /run/secrets/clickhouse_migration_password)
backup_password=$(read_secret /run/secrets/clickhouse_backup_password)
monitor_password=$(read_secret /run/secrets/clickhouse_monitor_password)

CLICKHOUSE_PASSWORD="$admin_password" clickhouse-client \
  --host banking_clickhouse --user "$CLICKHOUSE_ADMIN_USER" --multiquery <<SQL
CREATE DATABASE IF NOT EXISTS banking_recovery;
CREATE USER IF NOT EXISTS ${CLICKHOUSE_API_USER} IDENTIFIED WITH sha256_password BY '${api_password}';
ALTER USER ${CLICKHOUSE_API_USER} IDENTIFIED WITH sha256_password BY '${api_password}';
CREATE USER IF NOT EXISTS ${CLICKHOUSE_PROCESSOR_USER} IDENTIFIED WITH sha256_password BY '${processor_password}';
ALTER USER ${CLICKHOUSE_PROCESSOR_USER} IDENTIFIED WITH sha256_password BY '${processor_password}';
CREATE USER IF NOT EXISTS ${CLICKHOUSE_MIGRATION_USER} IDENTIFIED WITH sha256_password BY '${migration_password}';
ALTER USER ${CLICKHOUSE_MIGRATION_USER} IDENTIFIED WITH sha256_password BY '${migration_password}';
CREATE USER IF NOT EXISTS ${CLICKHOUSE_BACKUP_USER} IDENTIFIED WITH sha256_password BY '${backup_password}';
ALTER USER ${CLICKHOUSE_BACKUP_USER} IDENTIFIED WITH sha256_password BY '${backup_password}';
CREATE USER IF NOT EXISTS ${CLICKHOUSE_MONITOR_USER} IDENTIFIED WITH sha256_password BY '${monitor_password}';
ALTER USER ${CLICKHOUSE_MONITOR_USER} IDENTIFIED WITH sha256_password BY '${monitor_password}';

GRANT SELECT ON ${CLICKHOUSE_DB}.* TO ${CLICKHOUSE_API_USER};
GRANT SELECT, INSERT ON ${CLICKHOUSE_DB}.* TO ${CLICKHOUSE_PROCESSOR_USER};
GRANT SELECT, INSERT, CREATE TABLE, ALTER, DROP TABLE ON ${CLICKHOUSE_DB}.* TO ${CLICKHOUSE_MIGRATION_USER};
GRANT CREATE DATABASE ON ${CLICKHOUSE_DB}.* TO ${CLICKHOUSE_MIGRATION_USER};
GRANT SELECT ON ${CLICKHOUSE_DB}.* TO ${CLICKHOUSE_BACKUP_USER};
GRANT SELECT, INSERT, CREATE TABLE, DROP TABLE ON banking_recovery.* TO ${CLICKHOUSE_BACKUP_USER};
GRANT SELECT ON system.* TO ${CLICKHOUSE_MONITOR_USER};
SQL

echo "ClickHouse runtime identities are ready."
