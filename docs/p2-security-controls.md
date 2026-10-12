# P2 API security controls

## Durable sessions

Dashboard JWTs now contain a unique `jti` and an issue time. A token is valid
only while its matching `auth_sessions` row is unexpired, not revoked and still
belongs to an active user. This makes logout and account deactivation effective
immediately instead of waiting for JWT expiry.

Authenticated endpoints:

- `GET /api/auth/sessions` lists the caller's active sessions using only
  fingerprints for source and user-agent values;
- `POST /api/auth/logout` revokes the current session;
- `POST /api/auth/logout-all` revokes every active session for the caller.

Deploying this migration intentionally invalidates JWTs issued before durable
sessions existed because those tokens have no server-side session row.

## Rate limits

Redis stores fixed-window counters. Keys contain SHA-256 fingerprints rather
than raw usernames, tokens or client addresses.

| Scope | Default | Configuration |
| --- | ---: | --- |
| Login, per username and source | 10/minute | `LOGIN_RATE_LIMIT`, `LOGIN_RATE_WINDOW_SECONDS` |
| Authenticated API, per bearer token | 240/minute | `API_RATE_LIMIT`, `API_RATE_WINDOW_SECONDS` |

Login fails closed with `503` if Redis is unavailable. API requests also fail
closed because the platform is configured for an integrated local deployment.
Health and metrics endpoints are excluded so monitoring can still diagnose an
incident. A rejected request returns `429` with `Retry-After`.

## Audit evidence and retention

`security_events` records login success/denial, login throttling, logout and API
throttling. Source and attempted-subject identifiers are stored only as hashes;
details must never contain passwords, tokens or payloads. Rows are append-only
and cannot be deleted until `retain_until`, which defaults to 365 days.

Operational metrics:

- `banking_security_events_total{event_type,outcome}`;
- `banking_rate_limit_rejections_total{scope}`;
- `banking_active_sessions`.

The label sets are bounded. Usernames, addresses, session IDs and JWTs are not
Prometheus labels.

## Verification

```bash
python3 -m pytest tests/unit/test_security_controls.py -q
set -a; source .env; set +a
RUN_LIVE_E2E=1 python3 -m pytest \
  tests/integration/test_live_security_controls.py -q
```
