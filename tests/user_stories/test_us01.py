import pytest

from agents.code_repair import repair
from brain.state import BrainDecision, FailureClass


@pytest.mark.user_story("US-01")
def test_us01_code_bug_autonomous_repair(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "payments.py").write_text(
        "def process_transaction(amount: float, items: int) -> dict:\n"
        "    result = amount / 0\n"
        '    return {"result": result, "status": "ok"}\n',
        encoding="utf-8",
    )
    decision = BrainDecision(
        "us01",
        FailureClass.CODE_BUG,
        0.91,
        "sha-app",
        "PLAN_A",
        "ZeroDivisionError",
        None,
        None,
        False,
        [],
    )

    assert repair(decision, app_path=str(app_dir))
