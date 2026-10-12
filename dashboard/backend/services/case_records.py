"""Durable investigation case records with optimistic locking and audit."""

from __future__ import annotations

import json
from typing import Any

try:
    from services.alert_lifecycle import transition_allowed
except ModuleNotFoundError:  # Package import used by unit tests.
    from .alert_lifecycle import transition_allowed


PRIORITIES = frozenset({"P1", "P2", "P3", "P4"})
DISPOSITION_RESOLUTIONS = {
    "CONFIRMED_FRAUD": frozenset({"FRAUD_CONFIRMED", "REFERRED_TO_COMPLIANCE"}),
    "FALSE_POSITIVE": frozenset({"FALSE_POSITIVE"}),
    "DUPLICATE": frozenset({"DUPLICATE_CASE"}),
    "NO_ACTION": frozenset({"INSUFFICIENT_EVIDENCE"}),
    "REFERRED": frozenset({"REFERRED_TO_COMPLIANCE"}),
}
IGNORED_DISPOSITIONS = frozenset({"DUPLICATE", "NO_ACTION"})

CASE_COLUMNS = (
    "alert_id", "event_id", "payment_id", "account_id", "rule_name", "amount",
    "risk_score", "risk_level", "decision", "status", "xai_explanation", "notes",
    "evidence_file_url", "assignee_id", "version", "trace_id", "dataset_id", "run_id",
    "priority", "disposition", "due_at", "resolution_code", "closed_at", "closed_by",
    "created_at", "updated_at", "resolved_at",
)
CASE_SELECT = ", ".join(CASE_COLUMNS)


class CaseNotFoundError(LookupError):
    pass


class CaseScopeError(PermissionError):
    pass


class CaseVersionConflictError(RuntimeError):
    pass


class CaseTransitionError(ValueError):
    pass


def status_for_disposition(disposition: str) -> str:
    if disposition not in DISPOSITION_RESOLUTIONS:
        raise CaseTransitionError("Unsupported disposition")
    return "IGNORED" if disposition in IGNORED_DISPOSITIONS else "RESOLVED"


def resolution_allowed(disposition: str, resolution_code: str) -> bool:
    return resolution_code in DISPOSITION_RESOLUTIONS.get(disposition, frozenset())


def _load_scope(cursor: Any, alert_id: int, actor: dict[str, Any]) -> tuple[str, int | None, int, Any]:
    cursor.execute(
        "SELECT status, assignee_id, version, created_at FROM alerts WHERE alert_id = %s",
        (alert_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise CaseNotFoundError(alert_id)
    if actor["role"] != "ADMIN" and row[1] != actor["id"]:
        raise CaseScopeError(alert_id)
    return row


def _require_version(current: int, expected: int) -> None:
    if current != expected:
        raise CaseVersionConflictError("Case changed; refresh before updating")


def get_case(connection: Any, alert_id: int, actor: dict[str, Any]) -> dict[str, Any]:
    with connection.cursor() as cursor:
        _load_scope(cursor, alert_id, actor)
        cursor.execute(f"SELECT {CASE_SELECT} FROM alerts WHERE alert_id = %s", (alert_id,))
        case = dict(zip(CASE_COLUMNS, cursor.fetchone()))
        cursor.execute(
            "SELECT comment_id, author_user_id, body, created_at FROM alert_comments "
            "WHERE alert_id = %s ORDER BY created_at, comment_id",
            (alert_id,),
        )
        case["comments"] = [
            dict(zip(("comment_id", "author_user_id", "body", "created_at"), row))
            for row in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT evidence_id, object_key, original_filename, content_type, size_bytes, "
            "checksum_sha256, uploaded_by, created_at FROM evidence_files "
            "WHERE alert_id = %s ORDER BY created_at, evidence_id",
            (alert_id,),
        )
        case["evidence"] = [
            dict(zip((
                "evidence_id", "object_key", "original_filename", "content_type",
                "size_bytes", "checksum_sha256", "uploaded_by", "created_at",
            ), row))
            for row in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT audit_id, actor_user_id, action, old_status, new_status, details, created_at "
            "FROM alert_audit_log WHERE alert_id = %s ORDER BY created_at, audit_id",
            (alert_id,),
        )
        case["audit"] = [
            dict(zip((
                "audit_id", "actor_user_id", "action", "old_status", "new_status",
                "details", "created_at",
            ), row))
            for row in cursor.fetchall()
        ]
    return case


def update_case_metadata(
    connection: Any,
    alert_id: int,
    *,
    expected_version: int,
    actor: dict[str, Any],
    changes: dict[str, Any],
) -> dict[str, Any]:
    allowed = {key: value for key, value in changes.items() if key in {"priority", "due_at"}}
    if not allowed:
        raise CaseTransitionError("At least one case metadata field is required")
    if "priority" in allowed and allowed["priority"] not in PRIORITIES:
        raise CaseTransitionError("Unsupported priority")
    with connection.cursor() as cursor:
        old_status, _, current_version, created_at = _load_scope(cursor, alert_id, actor)
        _require_version(current_version, expected_version)
        if allowed.get("due_at") is not None and allowed["due_at"] < created_at:
            raise CaseTransitionError("due_at cannot precede case creation")
        assignments = [f"{column} = %s" for column in allowed]
        params = list(allowed.values())
        assignments.extend(("version = version + 1", "updated_at = NOW()"))
        cursor.execute(
            f"""WITH changed AS (
                UPDATE alerts SET {', '.join(assignments)}
                WHERE alert_id = %s AND version = %s
                RETURNING alert_id, version, priority, due_at
            ), audit AS (
                INSERT INTO alert_audit_log
                    (alert_id, actor_user_id, action, old_status, new_status, details)
                SELECT alert_id, %s, 'CASE_METADATA_UPDATED', %s, %s, %s::jsonb
                FROM changed RETURNING audit_id
            )
            SELECT changed.version, changed.priority, changed.due_at
            FROM changed JOIN audit ON TRUE""",
            (*params, alert_id, expected_version, actor["id"], old_status, old_status,
             json.dumps(allowed, default=str)),
        )
        changed = cursor.fetchone()
    if changed is None:
        raise CaseVersionConflictError("Case changed; refresh before updating")
    return {"version": changed[0], "priority": changed[1], "due_at": changed[2]}


def assign_case(
    connection: Any,
    alert_id: int,
    *,
    expected_version: int,
    assignee_id: int | None,
    actor: dict[str, Any],
) -> dict[str, Any]:
    if actor["role"] != "ADMIN":
        raise CaseScopeError("Only ADMIN can assign cases")
    with connection.cursor() as cursor:
        old_status, old_assignee, current_version, _ = _load_scope(cursor, alert_id, actor)
        _require_version(current_version, expected_version)
        if assignee_id is not None:
            cursor.execute(
                "SELECT role, is_active FROM users WHERE id = %s",
                (assignee_id,),
            )
            user = cursor.fetchone()
            if user is None or not user[1] or user[0] not in {"ADMIN", "ANALYST"}:
                raise CaseTransitionError("Assignee must be an active investigator")
        details = {"old_assignee_id": old_assignee, "new_assignee_id": assignee_id}
        cursor.execute(
            """WITH changed AS (
                UPDATE alerts
                SET assignee_id = %s, version = version + 1, updated_at = NOW()
                WHERE alert_id = %s AND version = %s
                RETURNING alert_id, version, assignee_id
            ), audit AS (
                INSERT INTO alert_audit_log
                    (alert_id, actor_user_id, action, old_status, new_status, details)
                SELECT alert_id, %s, 'CASE_ASSIGNED', %s, %s, %s::jsonb
                FROM changed RETURNING audit_id
            )
            SELECT changed.version, changed.assignee_id FROM changed JOIN audit ON TRUE""",
            (assignee_id, alert_id, expected_version, actor["id"], old_status, old_status,
             json.dumps(details)),
        )
        changed = cursor.fetchone()
    if changed is None:
        raise CaseVersionConflictError("Case changed; refresh before updating")
    return {"version": changed[0], "assignee_id": changed[1]}


def add_comment(
    connection: Any,
    alert_id: int,
    *,
    expected_version: int,
    body: str,
    actor: dict[str, Any],
) -> dict[str, Any]:
    body = body.strip()
    if not body or len(body) > 2000:
        raise CaseTransitionError("Comment must contain 1 to 2000 characters")
    with connection.cursor() as cursor:
        old_status, _, current_version, _ = _load_scope(cursor, alert_id, actor)
        _require_version(current_version, expected_version)
        cursor.execute(
            """WITH changed AS (
                UPDATE alerts SET version = version + 1, updated_at = NOW()
                WHERE alert_id = %s AND version = %s
                RETURNING alert_id, version
            ), comment AS (
                INSERT INTO alert_comments (alert_id, author_user_id, body)
                SELECT alert_id, %s, %s FROM changed
                RETURNING comment_id, alert_id, author_user_id, body, created_at
            ), audit AS (
                INSERT INTO alert_audit_log
                    (alert_id, actor_user_id, action, old_status, new_status, details)
                SELECT alert_id, %s, 'COMMENT_ADDED', %s, %s,
                       jsonb_build_object('comment_id', comment_id)
                FROM comment RETURNING audit_id
            )
            SELECT comment.comment_id, comment.author_user_id, comment.body,
                   comment.created_at, changed.version
            FROM comment JOIN changed USING (alert_id) JOIN audit ON TRUE""",
            (alert_id, expected_version, actor["id"], body, actor["id"], old_status, old_status),
        )
        changed = cursor.fetchone()
    if changed is None:
        raise CaseVersionConflictError("Case changed; refresh before updating")
    return {
        "comment_id": changed[0], "author_user_id": changed[1], "body": changed[2],
        "created_at": changed[3], "version": changed[4],
    }


def close_case(
    connection: Any,
    alert_id: int,
    *,
    expected_version: int,
    disposition: str,
    resolution_code: str,
    actor: dict[str, Any],
) -> dict[str, Any]:
    target_status = status_for_disposition(disposition)
    if not resolution_allowed(disposition, resolution_code):
        raise CaseTransitionError("Resolution code does not match disposition")
    with connection.cursor() as cursor:
        old_status, _, current_version, _ = _load_scope(cursor, alert_id, actor)
        _require_version(current_version, expected_version)
        if not transition_allowed(old_status, target_status):
            raise CaseTransitionError(
                f"Cannot apply disposition from {old_status}; case must be investigating"
            )
        details = {"disposition": disposition, "resolution_code": resolution_code}
        cursor.execute(
            """WITH changed AS (
                UPDATE alerts
                SET status = %s, disposition = %s, resolution_code = %s,
                    closed_at = NOW(), closed_by = %s, resolved_at = NOW(),
                    version = version + 1, updated_at = NOW()
                WHERE alert_id = %s AND version = %s
                RETURNING alert_id, status, disposition, resolution_code,
                          closed_at, closed_by, version
            ), audit AS (
                INSERT INTO alert_audit_log
                    (alert_id, actor_user_id, action, old_status, new_status, details)
                SELECT alert_id, %s, 'CASE_DISPOSITION', %s, status, %s::jsonb
                FROM changed RETURNING audit_id
            )
            SELECT changed.status, changed.disposition, changed.resolution_code,
                   changed.closed_at, changed.closed_by, changed.version
            FROM changed JOIN audit ON TRUE""",
            (target_status, disposition, resolution_code, actor["id"], alert_id,
             expected_version, actor["id"], old_status, json.dumps(details)),
        )
        changed = cursor.fetchone()
    if changed is None:
        raise CaseVersionConflictError("Case changed; refresh before updating")
    return dict(zip(
        ("status", "disposition", "resolution_code", "closed_at", "closed_by", "version"),
        changed,
    ))
