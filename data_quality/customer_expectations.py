"""Deterministic customer Silver expectation suite with row-level failures."""

from datetime import datetime, timedelta, timezone

import pandas as pd


REQUIRED_COLUMNS = {
    "customer_id", "account_id", "account_type", "balance", "account_status",
    "first_name", "last_name", "email", "phone", "address", "processed_at",
}
ACCOUNT_STATUSES = {"ACTIVE", "INACTIVE", "CLOSED", "BLOCKED"}
ACCOUNT_TYPES = {"SAVINGS", "CHECKING", "CURRENT", "FIXED_DEPOSIT"}


def evaluate_customer_silver(frame: pd.DataFrame, reference_accounts: set[str], now=None):
    """Return (run summary, invalid rows); each failure is tied to its record."""
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Silver schema missing columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("Silver customer batch is empty")
    now = now or datetime.now(timezone.utc)
    ids = frame["customer_id"].astype("string")
    accounts = frame["account_id"].astype("string")
    balances = pd.to_numeric(frame["balance"], errors="coerce")
    timestamps = pd.to_datetime(frame["processed_at"], errors="coerce", utc=True)

    checks = {
        "customer_id_not_null": ids.isna() | ids.str.strip().eq("").fillna(True),
        "account_id_not_null": accounts.isna() | accounts.str.strip().eq("").fillna(True),
        "account_id_unique": accounts.notna() & accounts.duplicated(keep=False),
        "balance_non_negative": balances.isna() | balances.lt(0),
        "account_status_enum": ~frame["account_status"].isin(ACCOUNT_STATUSES),
        "account_type_enum": ~frame["account_type"].isin(ACCOUNT_TYPES),
        "processed_at_valid": timestamps.isna() | timestamps.gt(now + timedelta(minutes=5)),
        "account_referential_integrity": accounts.notna() & ~accounts.isin(reference_accounts),
    }
    for column in ("first_name", "last_name"):
        values = frame[column].astype("string")
        checks[f"{column}_masked"] = values.notna() & ~values.str.fullmatch(r".\*{3}").fillna(False)
    email = frame["email"].astype("string")
    phone = frame["phone"].astype("string")
    address = frame["address"].astype("string")
    checks["email_masked"] = email.notna() & ~email.str.fullmatch(r"\*{3}@[^@\s]+").fillna(False)
    checks["phone_masked"] = phone.notna() & ~phone.str.fullmatch(r"\*{7}[0-9]{4}").fillna(False)
    checks["address_masked"] = address.notna() & address.ne("REDACTED").fillna(False)

    failures = pd.DataFrame({name: mask.fillna(True).astype(bool) for name, mask in checks.items()}, index=frame.index)
    invalid = frame.loc[failures.any(axis=1)].copy()
    invalid["_dq_errors"] = (
        failures.loc[invalid.index].apply(lambda row: ",".join(row.index[row.to_numpy()]), axis=1)
        if not invalid.empty else pd.Series(dtype="string", index=invalid.index)
    )
    summary = {
        "row_count": int(len(frame)),
        "invalid_count": int(len(invalid)),
        "duplicate_rate": float(checks["account_id_unique"].sum() / len(frame)),
        "checks": {name: {"failed_rows": int(mask.sum()), "passed": not bool(mask.any())}
                   for name, mask in failures.items()},
        "success": invalid.empty,
    }
    return summary, invalid
