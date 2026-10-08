from dashboard.backend.services.alert_lifecycle import transition_allowed


def test_alert_state_machine():
    assert transition_allowed("PENDING", "INVESTIGATING")
    assert transition_allowed("PENDING", "IGNORED")
    assert transition_allowed("INVESTIGATING", "RESOLVED")
    assert transition_allowed("INVESTIGATING", "IGNORED")
    assert transition_allowed("PENDING", "PENDING")
    assert not transition_allowed("PENDING", "RESOLVED")
    assert not transition_allowed("RESOLVED", "INVESTIGATING")
    assert not transition_allowed("IGNORED", "PENDING")
