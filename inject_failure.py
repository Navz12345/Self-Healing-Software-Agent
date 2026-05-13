import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from logger import get_logger

log = get_logger(__name__)


def _reset_app_log() -> None:
    Path("app/app.log").write_text("", encoding="utf-8")


def _run_container_command(command: list[str]) -> None:
    try:
        subprocess.run(command, check=False)
    except FileNotFoundError as exc:
        log.warning(
            "CONTAINER_COMMAND_SKIPPED",
            extra={"request_id": "none", "command": command[0], "error": str(exc)},
        )


def _probe_process_endpoint() -> None:
    url = "http://localhost:8000/process"
    for attempt in range(5):
        time.sleep(1)
        try:
            requests.get(url, timeout=2)
        except Exception as exc:
            log.info(
                "FAILURE_PROBE_ATTEMPTED",
                extra={"request_id": "none", "attempt": attempt + 1, "error": str(exc)},
            )


def inject_divide_by_zero():
    """
    Writes a buggy payments.py to the running container.
    Also makes a git commit so commit correlation can find it.
    """
    _reset_app_log()
    result = subprocess.run(
        ["git", "config", "user.email"],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        subprocess.run(["git", "config", "user.email", "demo@sha.local"], check=False)
        subprocess.run(["git", "config", "user.name", "SHA Demo"], check=False)
    timestamp = datetime.now().strftime("%H%M%S")
    buggy_code = """from logger import get_logger


log = get_logger(__name__)


def process_transaction(amount: float, items: int) -> dict:
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )
    result = amount / 0              # intentional divide-by-zero
    # injection_id: __TIMESTAMP__
    log.info("PROCESS_TRANSACTION_COMPLETE", extra={"request_id": "none", "result": result})
    return {"result": result, "status": "ok"}
""".replace(
        "__TIMESTAMP__", timestamp
    )
    with open("app/payments.py", "w", encoding="utf-8") as f:
        f.write(buggy_code)
    subprocess.run(["git", "add", "app/payments.py"], check=False)
    subprocess.run(
        ["git", "commit", "-m", f"refactor: optimize transaction calculation - {timestamp}"],
        check=False,
    )
    time.sleep(15)
    _run_container_command(["docker", "restart", "sha-app"])
    _probe_process_endpoint()
    log.info(
        "FAILURE_INJECTED",
        extra={
            "request_id": "none",
            "type": "divide_by_zero",
            "note": "waiting 15s before restart to allow log drone to detect errors",
        },
    )
    print("Injected: divide-by-zero in payments.py")


def inject_infra_crash():
    _reset_app_log()
    _run_container_command(["docker", "stop", "sha-app"])
    log.info("FAILURE_INJECTED", extra={"request_id": "none", "type": "infra_crash"})
    print("Injected: infrastructure crash (container stopped)")


def inject_ambiguous():
    """
    Raises error rate slightly but produces no matching log errors.
    Designed to keep GPT-4o confidence below 0.60 for US-04.
    """
    _reset_app_log()
    ambiguous_code = """from logger import get_logger


log = get_logger(__name__)
_call_count = 0


def process_transaction(amount: float, items: int) -> dict:
    global _call_count
    _call_count += 1
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )
    if _call_count in {1, 4}:
        raise ValueError("intermittent_failure")
    return {"result": amount / items, "status": "ok"}
"""
    with open("app/payments.py", "w", encoding="utf-8") as f:
        f.write(ambiguous_code)
    _run_container_command(["docker", "restart", "sha-app"])
    _probe_process_endpoint()
    log.info("FAILURE_INJECTED", extra={"request_id": "none", "type": "ambiguous"})
    print("Injected: ambiguous failure (mixed signals)")


if __name__ == "__main__":
    failure_type = sys.argv[1] if len(sys.argv) > 1 else "divide_by_zero"
    if failure_type == "--type":
        failure_type = sys.argv[2]
    {
        "divide_by_zero": inject_divide_by_zero,
        "infra_crash": inject_infra_crash,
        "ambiguous": inject_ambiguous,
    }[failure_type]()
