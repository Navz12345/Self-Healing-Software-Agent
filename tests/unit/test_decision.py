from brain.decision import route
from brain.state import BrainDecision, FailureClass


def test_route_low_confidence_to_escalate():
    decision = BrainDecision(
        "route1", FailureClass.ANOMALOUS_OUTPUT, 0.2, "sha-app", "PLAN_C", "", None, None, False, []
    )

    assert route(decision) == "escalate"


def test_route_plan_a_to_repair():
    decision = BrainDecision(
        "route2", FailureClass.CODE_BUG, 0.9, "sha-app", "PLAN_A", "", None, None, False, []
    )

    assert route(decision) == "repair"
