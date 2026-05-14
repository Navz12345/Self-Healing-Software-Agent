import os

import requests

from brain.state import BrainDecision, IncidentBundle
from logger import get_logger

log = get_logger(__name__)


def send_notification(
    decision: BrainDecision,
    bundle: IncidentBundle,
    resolved: bool = True,
) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook or "your/webhook/url" in webhook:
        log.warning("SLACK_NOT_CONFIGURED", extra={"request_id": decision.request_id})
        log.info(
            "SLACK_SENT",
            extra={
                "request_id": decision.request_id,
                "status_code": 0,
                "resolved": resolved,
                "configured": False,
            },
        )
        return

    status = "RESOLVED" if resolved else "ESCALATION_REQUIRED"
    message = {
        "text": f"*{status}* - Incident `{decision.request_id}`",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{status}* - `{decision.request_id}`"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{bundle.service}"},
                    {"type": "mrkdwn", "text": f"*Failure Class:*\n{decision.failure_class.value}"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{decision.confidence:.2f}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Suspect Commit:*\n{decision.suspect_commit or 'None'}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reasoning:*\n{decision.reasoning}"},
            },
        ],
    }

    try:
        resp = requests.post(webhook, json=message, timeout=5)  # type: ignore[arg-type]
        log.info(
            "SLACK_SENT",
            extra={
                "request_id": decision.request_id,
                "status_code": resp.status_code,
                "resolved": resolved,
            },
        )
    except Exception as exc:
        log.error("SLACK_SEND_FAILED", extra={"request_id": decision.request_id, "error": str(exc)})
