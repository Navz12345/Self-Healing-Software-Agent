import os
import subprocess
import time

import docker
import requests

from brain.state import BrainDecision
from logger import get_logger

log = get_logger(__name__)


def _health_url(default_url: str) -> str:
    configured = os.getenv("APP_URL", default_url).rstrip("/")
    if configured.endswith("/health"):
        return configured
    return configured + "/health"


def restart(
    decision: BrainDecision,
    container_name: str = "sha-app",
    health_url: str = "http://localhost:8000/health",
) -> bool:
    rid = decision.request_id
    health_url = _health_url(health_url)
    log.info("DEVOPS_RESTART", extra={"request_id": rid, "container": container_name})
    restarted = False
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        restarted = result.returncode == 0
    except FileNotFoundError as exc:
        log.warning("DOCKER_CLI_UNAVAILABLE", extra={"request_id": rid, "error": str(exc)})

    if not restarted:
        try:
            client = docker.from_env()
            client.containers.get(container_name).restart()
            restarted = True
        except Exception as exc:
            log.error("RESTART_FAILED", extra={"request_id": rid, "error": str(exc)})
            return False

    for attempt in range(12):
        time.sleep(5)
        try:
            resp = requests.get(health_url, timeout=3)
            if resp.status_code == 200:
                log.info(
                    "CONTAINER_RESTARTED",
                    extra={"request_id": rid, "attempts": attempt + 1},
                )
                return True
        except Exception as exc:
            log.warning(
                "HEALTH_RETRY_FAILED",
                extra={"request_id": rid, "attempt": attempt + 1, "error": str(exc)},
            )

    log.error("HEALTH_NOT_RESTORED", extra={"request_id": rid})
    return False
