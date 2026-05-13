import os

from brain.state import BrainDecision
from logger import get_logger

log = get_logger(__name__)


def route(decision: BrainDecision) -> str:
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    if decision.confidence < threshold:
        log.info(
            "DECISION_ROUTE_ESCALATE",
            extra={"request_id": decision.request_id, "confidence": decision.confidence},
        )
        return "escalate"
    if decision.proposed_plan in ("PLAN_A", "PLAN_B"):
        log.info(
            "DECISION_ROUTE_CODE_REPAIR",
            extra={"request_id": decision.request_id, "plan": decision.proposed_plan},
        )
        return "repair"
    log.info(
        "DECISION_ROUTE_DEVOPS",
        extra={"request_id": decision.request_id, "plan": decision.proposed_plan},
    )
    return "devops"
