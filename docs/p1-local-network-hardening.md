# P1 local network hardening — 2026-10-10

## Change

Every host port published by the local Docker Compose topology now binds to
`127.0.0.1`. This includes the dashboard, API, operator interfaces, metrics and
all datastore ports. Inter-container traffic continues to use the existing
Docker networks and service names.

A unit test parses `docker-compose.yml` and fails if a future published port
does not explicitly use the loopback address.

This is the appropriate default for the current single-machine demo. Remote
access should use an authenticated tunnel or a separately reviewed ingress;
datastore ports must not be widened directly to a LAN or the internet.

## Runtime verification

The stack was recreated without deleting volumes. Docker reported loopback
bindings for every published port, including PostgreSQL, Kafka, Redis, Neo4j,
ClickHouse, MinIO, the dashboard and its API.

Post-change checks passed:

- live integration suite: 8 passed;
- unit and data-quality suite: 65 passed, 3 intentionally skipped;
- backend readiness: PostgreSQL, Kafka, Redis, Neo4j, ClickHouse and MinIO ready;
- frontend: HTTP 200 on `127.0.0.1:5173`.

## Boundary

Loopback binding reduces local network exposure but is not a complete security
assessment. Production readiness still requires dependency/CVE review, TLS and
ingress design, least-privilege service identities, secret lifecycle controls,
container hardening and an application-level threat review.
