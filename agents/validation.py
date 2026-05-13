import os
import time

import requests

from brain.state import BrainDecision, IncidentBundle
from fmg.fmg import FMG
from logger import get_logger

log = get_logger(__name__)


def _health_url(default_url: str) -> str:
    configured = os.getenv("APP_URL", default_url).rstrip("/")
    if configured.endswith("/health"):
        return configured
    return configured + "/health"


def validate_and_close(
    decision: BrainDecision,
    bundle: IncidentBundle,
    health_url: str = "http://localhost:8000/health",
    fmg: FMG | None = None,
) -> bool:
    rid = decision.request_id
    health_url = _health_url(health_url)
    for attempt in range(3):
        time.sleep(5)
        try:
            resp = requests.get(health_url, timeout=3)
            if resp.status_code == 200:
                log.info("HEALTH_CONFIRMED", extra={"request_id": rid, "attempt": attempt + 1})
                if fmg:
                    fmg.store(
                        trajectory=bundle.signal_trajectory,
                        failure_class=decision.failure_class.value,
                        confidence=decision.confidence,
                        service=bundle.service,
                        cached_plan=decision.proposed_plan,
                        request_id=rid,
                    )
                    log.info("FMG_UPDATED", extra={"request_id": rid})
                from notify.slack import send_notification

                send_notification(decision, bundle, resolved=True)
                return True
        except Exception as exc:
            log.warning(
                "VALIDATION_RETRY_FAILED",
                extra={"request_id": rid, "attempt": attempt + 1, "error": str(exc)},
            )
    log.warning("VALIDATION_FAILED", extra={"request_id": rid})
    from notify.slack import send_notification

    send_notification(decision, bundle, resolved=False)
    return False
