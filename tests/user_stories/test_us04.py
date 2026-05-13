import time

import pytest

from brain.decision import route
from brain.diagnosis import diagnose
from brain.state import IncidentBundle, Signal


@pytest.mark.user_story("US-04")
def test_us04_low_confidence_escalation(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = IncidentBundle(
        "us04",
        "sha-app",
        [Signal("metric_drone", "sha-app", "error_rate", 0.4, 1.0, time.time(), "us04")],
        [0.1, 0.4],
        "",
        ["## AMBIGUOUS\nMixed signals should escalate"],
        1.0,
        time.time(),
    )

    decision = diagnose(bundle)

    assert decision.confidence < 0.60
    assert route(decision) == "escalate"
