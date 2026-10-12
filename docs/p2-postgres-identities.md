# PostgreSQL runtime identities and local secret provider

## Identity boundary

The hardened Compose overlay replaces the shared PostgreSQL owner credential
inside runtime services:

| Identity | Consumers | Effective access |
| --- | --- | --- |
| `banking_api` | Dashboard API | connect, read and application DML; no DDL |
| `banking_processor` | Replay, streaming, graph, reconciliation and Airflow jobs | connect, read and materialization DML including reconciliation replacement; no DDL |
| `banking_migration` | One-shot migration service | owns application schemas/objects and can run DDL; cannot assume the admin role and has no superuser attribute |
| `banking_backup` | Recovery runner | `pg_read_all_data` and temporary database creation; no application DML |
| `banking_monitor` | Database health and metrics collectors | PostgreSQL statistics plus read-only data access; no DML or DDL |

The original database owner is used only by the idempotent identity bootstrap.
It is not injected into API or processor containers by the secure overlay.

## Local Docker secrets

Create the git-ignored provider directory once:

```bash
python3 scripts/security/bootstrap_local_secrets.py
```

The command copies the existing PostgreSQL owner password into an admin-only
bootstrap file and creates five random dedicated passwords. Values are never
printed. `.runtime/secrets` is mode `0700`; each read-only file is mode `0444`
so non-root containers can consume an explicitly mounted Docker secret while
other host users cannot traverse the provider directory. Existing dedicated
values are preserved unless `--rotate` is supplied.

Start or update the hardened stack with both Compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d --build
```

The startup order is PostgreSQL health, identity bootstrap, one-shot migration,
then API/processors. `RUN_DB_MIGRATIONS=false` prevents the API role from
performing DDL.

The base Compose file remains a compatibility path for local diagnosis. The
secure overlay is the required pre-production path. A managed deployment must
replace local files with its approved secret manager; do not copy
`.runtime/secrets` into an image or repository.

## Verification and rotation

```bash
set -a; source .env; set +a
RUN_SECURE_E2E=1 python3 -m pytest \
  tests/integration/test_live_postgres_identities.py -q
python3 scripts/backup/rehearse_multistore_restore.py --stores postgresql \
  --skip-reconciliation
```

To rotate dedicated identities, run the generator with `--rotate`, then rerun
the secure Compose command. The identity bootstrap applies the new password
before dependent services restart. Rotate one datastore family at a time and
run its permission-denial and recovery checks before continuing.
