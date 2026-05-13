import time

from brain.diagnosis import diagnose
from brain.state import IncidentBundle, Signal


def test_diagnosis_offline_code_bug(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = IncidentBundle(
        request_id="diagtest",
        service="sha-app",
        signals=[
            Signal("log_drone", "sha-app", "log_error_density", 0.7, 1.0, time.time(), "diagtest"),
            Signal("metric_drone", "sha-app", "error_rate", 0.8, 1.0, time.time(), "diagtest"),
        ],
        signal_trajectory=[0.1, 0.8],
        recent_commits="256fa22 refactor transaction calculation\napp/payments.py",
        retrieved_chunks=["## CODE_BUG\nZeroDivisionError"],
        weighted_vote=2.0,
        timestamp=time.time(),
    )

    decision = diagnose(bundle)

    assert decision.failure_class.value == "CODE_BUG"
    assert decision.proposed_plan == "PLAN_A"
    assert decision.suspect_commit.startswith("256fa22")


def test_diagnosis_offline_ambiguous_low_confidence(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = IncidentBundle(
        request_id="ambig",
        service="sha-app",
        signals=[Signal("metric_drone", "sha-app", "error_rate", 0.3, 1.0, time.time(), "ambig")],
        signal_trajectory=[0.1, 0.3],
        recent_commits="",
        retrieved_chunks=["## AMBIGUOUS\nMixed intermittent failure"],
        weighted_vote=1.0,
        timestamp=time.time(),
    )

    decision = diagnose(bundle)

    assert decision.confidence < 0.60
