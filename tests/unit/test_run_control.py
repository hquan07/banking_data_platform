import pytest

from dashboard.backend.services.run_control import (
    RUN_STATES,
    TERMINAL_STATES,
    RunTransitionError,
    summarize_offset_progress,
    transition_allowed,
)


def test_run_state_machine_happy_path():
    path = [
        "CREATED", "RUNNING", "PAUSING", "PAUSED",
        "RUNNING", "CANCELLING", "CANCELLED",
    ]
    assert all(transition_allowed(old, new) for old, new in zip(path, path[1:]))


@pytest.mark.parametrize("terminal", TERMINAL_STATES)
def test_terminal_run_states_are_immutable(terminal):
    assert all(not transition_allowed(terminal, state) for state in RUN_STATES)


def test_invalid_shortcuts_are_rejected():
    assert transition_allowed("RUNNING", "COMPLETED")
    assert transition_allowed("RUNNING", "FAILED")
    assert not transition_allowed("CREATED", "COMPLETED")
    assert not transition_allowed("RUNNING", "PAUSED")
    assert not transition_allowed("PAUSED", "COMPLETED")
    assert not transition_allowed("CANCELLING", "RUNNING")


def test_transition_error_is_a_value_error():
    assert isinstance(RunTransitionError("invalid"), ValueError)


def test_offset_progress_is_bounded_and_reports_lag():
    assert summarize_offset_progress([
        (10, 20, 16),
        (30, 40, 50),
        (50, None, None),
    ]) == {
        "processed": 16,
        "total": 20,
        "percent": 80.0,
        "lag": 4,
        "partitions": 2,
    }


def test_offset_progress_does_not_infer_completion_from_empty_windows():
    assert summarize_offset_progress([]) == {
        "processed": 0,
        "total": 0,
        "percent": None,
        "lag": 0,
        "partitions": 0,
    }
