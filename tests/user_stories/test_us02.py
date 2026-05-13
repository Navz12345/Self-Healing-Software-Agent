import subprocess

import pytest

from agents import devops
from brain.state import BrainDecision, FailureClass


@pytest.mark.user_story("US-02")
def test_us02_infrastructure_crash_recovery(monkeypatch):
    monkeypatch.setattr(devops.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        devops.subprocess,
        "run",
        lambda *_, **__: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="sha-app", stderr=""
        ),
    )

    class Resp:
        status_code = 200

    monkeypatch.setattr(devops.requests, "get", lambda *_, **__: Resp())
    decision = BrainDecision(
        "us02",
        FailureClass.INFRA_CRASH,
        0.88,
        "sha-app",
        "PLAN_C",
        "container stopped",
        None,
        None,
        False,
        [],
    )

    assert devops.restart(decision)
