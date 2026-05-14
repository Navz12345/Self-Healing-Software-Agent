import os
import shutil
import subprocess
from pathlib import Path

import docker
from openai import OpenAI

from brain.state import BrainDecision
from logger import get_logger

log = get_logger(__name__)
_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    global _client
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "sk-your-key-here":
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def _strip_code_fences(code: str) -> str:
    patched_code = code.strip()
    if patched_code.startswith("```"):
        patched_code = patched_code.split("\n", 1)[1].rsplit("```", 1)[0]
    return patched_code


def _generate_patch(current_code: str, decision: BrainDecision) -> str:
    client = _get_client()
    rid = decision.request_id
    if client is None:
        patched_code = current_code.replace("amount / 0", "amount / items")
        if patched_code != current_code:
            log.info(
                "PATCH_GENERATED_OFFLINE", extra={"request_id": rid, "strategy": "divide_by_zero"}
            )
            return patched_code
        log.warning("PATCH_OFFLINE_NOOP", extra={"request_id": rid})
        return current_code

    prompt = f"""The following Python function has a bug causing: {decision.reasoning}

Current code:
```python
{current_code}
```

Write a corrected version of the ENTIRE file. Return ONLY the Python code, no markdown fences."""
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content or ""
    return _strip_code_fences(content)


def _prepare_sandbox(app_path: Path, sandbox_app_path: Path, patched_code: str, rid: str) -> None:
    sandbox_app_path.mkdir(exist_ok=True)
    for source in app_path.glob("*.py"):
        shutil.copy2(source, sandbox_app_path / source.name)
    (sandbox_app_path / "payments.py").write_text(patched_code, encoding="utf-8")
    root_logger = Path("logger.py")
    if root_logger.exists():
        shutil.copy2(root_logger, sandbox_app_path / "logger.py")
    log.info(
        "SANDBOX_PATCH_WRITTEN",
        extra={"request_id": rid, "path": str(sandbox_app_path / "payments.py")},
    )


def _docker_exec(container_name: str, command: list[str], rid: str) -> tuple[bool, str]:
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        result = container.exec_run(command)
        output = result.output.decode("utf-8", errors="replace")
        return result.exit_code == 0, output
    except Exception as exc:
        log.warning(
            "DOCKER_SDK_EXEC_FAILED",
            extra={"request_id": rid, "container": container_name, "error": str(exc)},
        )
        return False, str(exc)


def _restart_container(container_name: str, rid: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True
        log.warning("DOCKER_CLI_RESTART_FAILED", extra={"request_id": rid, "error": result.stderr})
    except FileNotFoundError as exc:
        log.warning("DOCKER_CLI_UNAVAILABLE", extra={"request_id": rid, "error": str(exc)})

    try:
        client = docker.from_env()
        client.containers.get(container_name).restart()
        return True
    except Exception as exc:
        log.error("DOCKER_SDK_RESTART_FAILED", extra={"request_id": rid, "error": str(exc)})
        return False


def _run_sandbox_tests(rid: str, sandbox_app_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "sha-sandbox",
                "python",
                "-m",
                "pytest",
                "test_sandbox.py",
                "-q",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return result.returncode == 0, result.stdout[-500:] + result.stderr[-500:]
    except FileNotFoundError as exc:
        log.warning("SANDBOX_DOCKER_UNAVAILABLE", extra={"request_id": rid, "error": str(exc)})
        sdk_passed, sdk_output = _docker_exec(
            "sha-sandbox",
            ["python", "-m", "pytest", "test_sandbox.py", "-q", "--tb=short"],
            rid,
        )
        if sdk_passed:
            return True, sdk_output[-500:]
        result = subprocess.run(
            ["python", "-m", "py_compile", str(sandbox_app_path / "payments.py")],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0, result.stdout[-500:] + result.stderr[-500:]


def repair(
    decision: BrainDecision,
    app_path: str = "app",
    sandbox_url: str = "http://localhost:9000",
) -> bool:
    rid = decision.request_id
    app_dir = Path(app_path)

    if decision.suspect_commit:
        log.info(
            "COMMIT_REVERT_ATTEMPT",
            extra={"request_id": rid, "commit": decision.suspect_commit},
        )
        reverted = _try_revert(decision.suspect_commit, rid)
        if reverted:
            return True

    current_code = (app_dir / "payments.py").read_text(encoding="utf-8")
    patched_code = _generate_patch(current_code, decision)
    sandbox_app_path = app_dir / "../sandbox_app"
    _prepare_sandbox(app_dir, sandbox_app_path, patched_code, rid)

    log.info(
        "PATCH_GENERATED",
        extra={
            "request_id": rid,
            "lines": len(patched_code.splitlines()),
            "sandbox_url": sandbox_url,
        },
    )

    sandbox_pass, output = _run_sandbox_tests(rid, sandbox_app_path)
    log.info(
        "SANDBOX_RESULT",
        extra={"request_id": rid, "passed": sandbox_pass, "output": output[-500:]},
    )

    if sandbox_pass:
        (app_dir / "payments.py").write_text(patched_code, encoding="utf-8")
        _restart_container("sha-app", rid)
        log.info("PATCH_PROMOTED", extra={"request_id": rid})
        return True

    log.warning("SANDBOX_FAILED", extra={"request_id": rid})
    return False


def _try_revert(commit_hash: str, rid: str) -> bool:
    """Revert suspect commit and test the result."""
    result = subprocess.run(
        ["git", "revert", "--no-commit", commit_hash],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log.warning("REVERT_FAILED", extra={"request_id": rid, "error": result.stderr})
        return False

    test_result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if test_result.returncode == 0:
        subprocess.run(
            ["git", "commit", "-m", f"auto-revert: {commit_hash} caused incident {rid}"],
            check=False,
        )
        log.info("REVERT_PROMOTED", extra={"request_id": rid, "commit": commit_hash})
        return True

    abort = subprocess.run(
        ["git", "revert", "--abort"], capture_output=True, text=True, check=False
    )
    log.warning(
        "REVERT_TEST_FAILED",
        extra={
            "request_id": rid,
            "output": test_result.stdout[-300:],
            "abort_status": abort.returncode,
        },
    )
    return False
