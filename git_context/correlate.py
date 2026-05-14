import subprocess
from datetime import datetime, timedelta
from typing import Optional

from logger import get_logger

log = get_logger(__name__)


def get_recent_commits(repo_path: str = ".", hours: int = 6, request_id: str = "none") -> str:
    """
    Returns git log output for commits in the last `hours` hours.
    Format: one-line summary + list of changed files per commit.
    """
    since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    result = subprocess.run(
        ["git", "log", f"--since={since}", "--oneline", "--name-only", "--no-merges"],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    output = result.stdout.strip()
    log.info(
        "GIT_COMMITS_FETCHED",
        extra={
            "request_id": request_id,
            "commit_count": output.count("\n\n") + 1 if output else 0,
            "since_hours": hours,
        },
    )
    return output if output else "No recent commits in the last 6 hours."


def extract_suspect_commit(
    git_log: str,
    error_file: str = "payments.py",
    request_id: str = "none",
) -> Optional[str]:
    """
    Scans the git log output for commits that touched error_file.
    Returns the commit summary line of the most recent matching commit.
    """
    lines = git_log.splitlines()
    current_commit_line = None
    for line in lines:
        if line and not line.startswith(" "):
            parts = line.split(" ", 1)
            if 7 <= len(parts[0]) <= 8:
                current_commit_line = line
        if error_file in line and current_commit_line:
            log.info(
                "SUSPECT_COMMIT_FOUND",
                extra={
                    "request_id": request_id,
                    "commit": current_commit_line,
                    "error_file": error_file,
                },
            )
            return current_commit_line
    log.info("SUSPECT_COMMIT_NOT_FOUND", extra={"request_id": request_id, "error_file": error_file})
    return None

