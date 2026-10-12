# P1 PostgreSQL recovery rehearsal — 2026-10-10

## Workflow

Run the following command from the repository root while the PostgreSQL
container is healthy:

```bash
./scripts/backup/backup_db.sh
```

The command now performs the complete verification workflow rather than only
writing a dump:

1. creates a custom-format archive in a process temporary directory;
2. validates the archive table of contents with `pg_restore --list`;
3. creates a uniquely named database in the existing PostgreSQL container;
4. restores the archive with ownership and ACL replay disabled;
5. compares exact row counts for every non-system table;
6. removes the temporary database even when restore or validation fails;
7. writes a local JSON report containing the archive hash and reconciliation,
   then deletes the raw archive.

An existing archive can be checked again without creating another dump:

```bash
./scripts/backup/backup_db.sh --archive /secure/path/postgres_<timestamp>.dump
```

Only reports are retained under `.runtime/backups`. An archive supplied through
`--archive` is read but never deleted. Production backups belong in an
encrypted, access-controlled backup target with an explicit retention policy.

## Result

`PASS`.

| Check | Result |
| --- | ---: |
| Archive size | 6,483,697 bytes |
| Restore entries | 174 |
| Tables reconciled | 24 |
| Source rows | 191,611 |
| Restored rows | 191,611 |
| Count differences | 0 |
| Rehearsal duration | 2.864 seconds |
| Temporary database removed | yes |

The archive SHA-256 recorded for this historical run was
`2520a93efbbc2206c294bf24f83a349fc8322e4c05eb9c541415e877d8ea3f40`;
the raw local archive is no longer part of the retained evidence policy.

## Boundary

This rehearsal covers the PostgreSQL system of record only. Kafka can be
repopulated from retained source datasets for this demo, but production use
still needs independently tested retention and recovery procedures for Kafka,
MinIO, ClickHouse, Neo4j, Redis, Spark checkpoints and Superset metadata.
