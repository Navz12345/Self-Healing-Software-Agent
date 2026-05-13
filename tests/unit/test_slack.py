import time

from brain.state import BrainDecision, FailureClass, IncidentBundle
from notify.slack import send_notification


def test_slack_no_webhook_is_noop(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    decision = BrainDecision(
        "slack1", FailureClass.CODE_BUG, 0.9, "sha-app", "PLAN_A", "fixed", None, None, False, []
    )
    bundle = IncidentBundle("slack1", "sha-app", [], [], "", [], 0.0, time.time())

    send_notification(decision, bundle, resolved=True)


def test_slack_posts_when_configured(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")

    class Resp:
        status_code = 200

    sent = {}
    monkeypatch.setattr(
        "notify.slack.requests.post",
        lambda url, json, timeout: sent.update({"url": url, "json": json}) or Resp(),
    )
    decision = BrainDecision(
        "slack2", FailureClass.CODE_BUG, 0.9, "sha-app", "PLAN_A", "fixed", None, None, False, []
    )
    bundle = IncidentBundle("slack2", "sha-app", [], [], "", [], 0.0, time.time())

    send_notification(decision, bundle, resolved=True)

    assert sent["json"]["text"].startswith("*RESOLVED*")
