#!/usr/bin/env bash
set -euo pipefail

read_secret() {
  local path="$1"
  local value
  value=$(tr -d '\r\n' < "$path")
  if [[ ! "$value" =~ ^[A-Za-z0-9_-]{32,128}$ ]]; then
    echo "Dedicated PostgreSQL secret has an invalid format: $path" >&2
    exit 1
  fi
  printf '%s' "$value"
}

export PGPASSWORD
PGPASSWORD=$(tr -d '\r\n' < /run/secrets/postgres_admin_password)

api_password=$(read_secret /run/secrets/postgres_api_password)
processor_password=$(read_secret /run/secrets/postgres_processor_password)
migration_password=$(read_secret /run/secrets/postgres_migration_password)
backup_password=$(read_secret /run/secrets/postgres_backup_password)
monitor_password=$(read_secret /run/secrets/postgres_monitor_password)

psql -v ON_ERROR_STOP=1 \
  -h banking_postgres \
  -U "$POSTGRES_ADMIN_USER" \
  -d "$POSTGRES_DB" \
  -v database="$POSTGRES_DB" \
  -v admin_user="$POSTGRES_ADMIN_USER" \
  -v api_user="$POSTGRES_API_USER" \
  -v api_password="$api_password" \
  -v processor_user="$POSTGRES_PROCESSOR_USER" \
  -v processor_password="$processor_password" \
  -v migration_user="$POSTGRES_MIGRATION_USER" \
  -v migration_password="$migration_password" \
  -v backup_user="$POSTGRES_BACKUP_USER" \
  -v backup_password="$backup_password" \
  -v monitor_user="$POSTGRES_MONITOR_USER" \
  -v monitor_password="$monitor_password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'api_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'api_user') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'processor_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'processor_user') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'migration_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migration_user') \gexec
SELECT format('CREATE ROLE %I LOGIN CREATEDB', :'backup_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'backup_user') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'monitor_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'monitor_user') \gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'api_user', :'api_password'
) \gexec
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'processor_user', :'processor_password'
) \gexec
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER CREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'migration_user', :'migration_password'
) \gexec
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER CREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'backup_user', :'backup_password'
) \gexec
SELECT format(
    'ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'monitor_user', :'monitor_password'
) \gexec

SELECT format('ALTER SCHEMA %I OWNER TO %I', schema_name, :'migration_user')
FROM (VALUES ('public'), ('core_banking'), ('data_warehouse')) AS schemas(schema_name)
WHERE EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = schema_name) \gexec

SELECT format(
    'ALTER %s %I.%I OWNER TO %I',
    CASE object.relkind
        WHEN 'S' THEN 'SEQUENCE'
        WHEN 'v' THEN 'VIEW'
        WHEN 'm' THEN 'MATERIALIZED VIEW'
        WHEN 'f' THEN 'FOREIGN TABLE'
        ELSE 'TABLE'
    END,
    object.schema_name,
    object.object_name,
    :'migration_user'
)
FROM (
    SELECT namespace.nspname AS schema_name, class.relname AS object_name, class.relkind
    FROM pg_class AS class
    JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
    WHERE namespace.nspname IN ('public', 'core_banking', 'data_warehouse')
      AND class.relkind IN ('r', 'p', 'S', 'v', 'm', 'f')
      AND pg_get_userbyid(class.relowner) = :'admin_user'
      AND NOT EXISTS (
          SELECT 1 FROM pg_depend
          WHERE classid = 'pg_class'::regclass
            AND objid = class.oid AND deptype = 'e'
      )
      AND NOT (
          class.relkind = 'S' AND EXISTS (
              SELECT 1 FROM pg_depend
              WHERE classid = 'pg_class'::regclass
                AND objid = class.oid AND deptype IN ('a', 'i')
          )
      )
) AS object \gexec

SELECT format(
    'ALTER %s %I.%I(%s) OWNER TO %I',
    CASE routine.prokind WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END,
    namespace.nspname,
    routine.proname,
    pg_get_function_identity_arguments(routine.oid),
    :'migration_user'
)
FROM pg_proc AS routine
JOIN pg_namespace AS namespace ON namespace.oid = routine.pronamespace
WHERE namespace.nspname IN ('public', 'core_banking', 'data_warehouse')
  AND routine.prokind IN ('f', 'p')
  AND pg_get_userbyid(routine.proowner) = :'admin_user'
  AND NOT EXISTS (
      SELECT 1 FROM pg_depend
      WHERE classid = 'pg_proc'::regclass
        AND objid = routine.oid AND deptype = 'e'
  ) \gexec

SELECT format('REVOKE %I FROM %I', :'admin_user', :'migration_user')
WHERE pg_has_role(:'migration_user', :'admin_user', 'MEMBER') \gexec

GRANT CREATE ON DATABASE :"database" TO :"migration_user";
GRANT CONNECT ON DATABASE :"database" TO :"api_user", :"processor_user", :"backup_user", :"monitor_user";
GRANT USAGE ON SCHEMA public, core_banking, data_warehouse
    TO :"api_user", :"processor_user", :"backup_user", :"monitor_user";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public, core_banking, data_warehouse
    TO :"api_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public, core_banking, data_warehouse
    TO :"processor_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public, core_banking, data_warehouse
    TO :"api_user", :"processor_user";
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public, core_banking, data_warehouse
    TO :"api_user", :"processor_user";
GRANT pg_read_all_data TO :"backup_user";
GRANT pg_monitor TO :"monitor_user";
GRANT pg_read_all_data TO :"monitor_user";

ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO :"api_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"api_user", :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO :"api_user", :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA core_banking
    GRANT SELECT, INSERT, UPDATE ON TABLES TO :"api_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA core_banking
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA core_banking
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"api_user", :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA core_banking
    GRANT EXECUTE ON FUNCTIONS TO :"api_user", :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA data_warehouse
    GRANT SELECT, INSERT, UPDATE ON TABLES TO :"api_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA data_warehouse
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA data_warehouse
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"api_user", :"processor_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA data_warehouse
    GRANT EXECUTE ON FUNCTIONS TO :"api_user", :"processor_user";
SQL

echo "PostgreSQL runtime identities are ready."
