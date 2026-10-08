"""Allowed case-management transitions, shared by API and tests."""

TRANSITIONS = {
    "PENDING": frozenset({"INVESTIGATING", "IGNORED"}),
    "INVESTIGATING": frozenset({"RESOLVED", "IGNORED"}),
    "RESOLVED": frozenset(),
    "IGNORED": frozenset(),
}


def transition_allowed(current: str, target: str) -> bool:
    return current == target or target in TRANSITIONS.get(current, ())
