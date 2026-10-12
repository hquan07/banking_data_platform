# Investigation case contract

The alert row is the durable case record. Every mutation uses its `version` as
an optimistic compare-and-swap token and writes an `alert_audit_log` entry in
the same PostgreSQL statement.

## Case lifecycle

- `PENDING -> INVESTIGATING` starts analyst work.
- `INVESTIGATING -> RESOLVED` requires a confirmed-fraud, false-positive or
  referred disposition through `POST /api/alerts/{id}/disposition`.
- `INVESTIGATING -> IGNORED` requires duplicate or no-action disposition.
- Existing status clients remain compatible, but the disposition endpoint is
  the complete closure contract because it records `resolution_code`,
  `closed_at` and `closed_by`.

Priorities are `P1` through `P4`; new cases default to `P3`. Due dates must be
timezone-aware and cannot precede case creation.

## Authorization

- ADMIN can read every case, change metadata and assign or unassign an active
  ADMIN/ANALYST investigator.
- ANALYST can read and mutate only cases assigned to their current database
  identity.
- Export remains ADMIN-only and includes priority, disposition, due date,
  resolution and closure fields.

Authorization is evaluated from the current database role on every request;
JWT claims do not grant stale access after a role change.

## Comments and evidence

`POST /api/alerts/{id}/comments` is append-only. There is no update or delete
API. A successful insert increments the case version and adds a
`COMMENT_ADDED` audit event.

Evidence uses a server-generated object key. Before upload, request
`GET /api/evidence/presigned-url` with filename, case ID, content type and the
lowercase SHA-256 digest. Send every returned `required_headers` value with the
PUT, then complete the record with the current case version. Completion checks:

1. object ownership and case scope;
2. optimistic case version;
3. object size (maximum 25 MiB) and content type;
4. SHA-256 metadata and a server-computed SHA-256 of the object bytes;
5. unique, immutable evidence metadata and an `EVIDENCE_UPLOADED` audit event.

MinIO objects are never updated or deleted through the application API.
