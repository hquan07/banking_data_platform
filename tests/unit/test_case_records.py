import pytest

from dashboard.backend.services.case_records import (
    CaseTransitionError,
    resolution_allowed,
    status_for_disposition,
)


@pytest.mark.parametrize(
    ("disposition", "status"),
    [
        ("CONFIRMED_FRAUD", "RESOLVED"),
        ("FALSE_POSITIVE", "RESOLVED"),
        ("REFERRED", "RESOLVED"),
        ("DUPLICATE", "IGNORED"),
        ("NO_ACTION", "IGNORED"),
    ],
)
def test_disposition_maps_to_terminal_case_state(disposition, status):
    assert status_for_disposition(disposition) == status


def test_resolution_code_must_match_disposition():
    assert resolution_allowed("CONFIRMED_FRAUD", "FRAUD_CONFIRMED")
    assert resolution_allowed("CONFIRMED_FRAUD", "REFERRED_TO_COMPLIANCE")
    assert resolution_allowed("FALSE_POSITIVE", "FALSE_POSITIVE")
    assert not resolution_allowed("FALSE_POSITIVE", "FRAUD_CONFIRMED")
    assert not resolution_allowed("DUPLICATE", "INSUFFICIENT_EVIDENCE")


def test_unknown_disposition_is_rejected():
    with pytest.raises(CaseTransitionError):
        status_for_disposition("UNKNOWN")
