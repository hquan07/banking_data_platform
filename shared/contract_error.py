"""Safe, structured contract failures and dead-letter envelopes."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


def payload_fingerprint(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint without retaining the payload."""
    if isinstance(payload, bytes):
        encoded = payload
    elif isinstance(payload, str):
        encoded = payload.encode("utf-8", errors="replace")
    else:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str,
        ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trace_id(payload: Any) -> str | None:
    candidate = payload
    if isinstance(payload, bytes):
        try:
            candidate = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
    elif isinstance(payload, str):
        try:
            candidate = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(candidate, Mapping):
        return None
    value = candidate.get("trace_id")
    return value if isinstance(value, str) and value else None


def safe_reason(value: str) -> str:
    """Normalize an error label so exception text cannot leak record data."""
    reason = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return reason[:120] or "contract_validation_failed"


@dataclass(eq=False)
class ContractError(ValueError):
    """A contract failure with safe context suitable for a DLQ record."""

    contract: str
    version: int
    reason: str
    trace_id: str | None
    source_topic: str
    payload_fingerprint: str

    def __init__(
        self,
        contract: str,
        version: int,
        reason: str,
        payload: Any,
        source_topic: str,
    ) -> None:
        self.contract = contract
        self.version = version
        self.reason = safe_reason(reason)
        self.trace_id = _trace_id(payload)
        self.source_topic = source_topic
        self.payload_fingerprint = payload_fingerprint(payload)
        super().__init__(self.reason)


def build_dlq_envelope(
    error: BaseException,
    payload: Any,
    source: Mapping[str, Any],
    *,
    contract: str,
    version: int = 1,
) -> dict[str, Any]:
    """Build the common v1 DLQ envelope without copying the source payload."""
    if isinstance(error, ContractError):
        contract = error.contract
        version = error.version
        reason = error.reason
        trace_id = error.trace_id
    elif isinstance(error, json.JSONDecodeError):
        reason = "malformed_json"
        trace_id = _trace_id(payload)
    elif isinstance(error, UnicodeDecodeError):
        reason = "invalid_encoding"
        trace_id = None
    else:
        reason = safe_reason(type(error).__name__)
        trace_id = _trace_id(payload)

    topic = source.get("topic") or (
        error.source_topic if isinstance(error, ContractError) else None
    )
    transport = {
        "topic": topic,
        "partition": source.get("partition"),
        "offset": source.get("offset"),
    }
    if source.get("timestamp") is not None:
        transport["timestamp"] = source["timestamp"]
    return {
        "schema_version": 1,
        "contract": contract,
        "contract_version": version,
        "reason": reason,
        "trace_id": trace_id,
        "payload_fingerprint": payload_fingerprint(payload),
        "source": transport,
    }
