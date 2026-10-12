# ClickHouse runtime identities

The secure Compose overlay rotates the ClickHouse administrator credential and
keeps it only in the server and one-shot identity bootstrap. Runtime workloads
use separate file-backed credentials:

| Identity | Consumer | Access |
| --- | --- | --- |
| `banking_ch_api` | Dashboard API | application `SELECT` only |
| `banking_ch_processor` | Payment stream, reconciliation and Airflow | application `SELECT` and `INSERT`; no DDL |
| `banking_ch_migration` | One-shot schema migration | application schema DDL and DML |
| `banking_ch_monitor` | Health/metrics collector | `system.*` read only |
| `banking_ch_backup` | Isolated recovery rehearsal | read source data and create/drop tables only in `banking_recovery`; no database-level DDL |

Generate or refresh local files with
`python3 scripts/security/bootstrap_local_secrets.py`, then start the secure
overlay. `clickhouse_identity_init` rotates users and grants, after which
`clickhouse_migrate` applies the schema before API/processors start.

Verification:

```bash
set -a; source .env; set +a
RUN_SECURE_E2E=1 python3 -m pytest \
  tests/integration/test_live_clickhouse_identities.py -q
CLICKHOUSE_BACKUP_USER=banking_ch_backup \
CLICKHOUSE_BACKUP_PASSWORD_FILE=.runtime/secrets/clickhouse_backup_password \
CLICKHOUSE_RECOVERY_DB=banking_recovery \
python3 scripts/backup/rehearse_multistore_restore.py \
  --stores clickhouse --skip-reconciliation
```
