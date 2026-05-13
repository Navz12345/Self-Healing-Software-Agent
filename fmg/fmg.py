import json
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from logger import get_logger

log = get_logger(__name__)

CREATE_SIGNATURES = """
CREATE TABLE IF NOT EXISTS failure_signatures (
    id              TEXT PRIMARY KEY,
    trajectory      TEXT NOT NULL,
    failure_class   TEXT NOT NULL,
    confidence      REAL NOT NULL,
    service         TEXT NOT NULL,
    cached_plan     TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    created_at      REAL NOT NULL
)
"""

CREATE_FIX_ATTEMPTS = """
CREATE TABLE IF NOT EXISTS fix_attempts (
    id              TEXT PRIMARY KEY,
    signature_id    TEXT NOT NULL,
    plan_type       TEXT NOT NULL,
    sandbox_result  TEXT NOT NULL,
    production_ok   INTEGER,
    created_at      REAL NOT NULL,
    FOREIGN KEY (signature_id) REFERENCES failure_signatures(id)
)
"""


def _dtw_distance(seq_a: list, seq_b: list) -> float:
    """
    Dynamic Time Warping distance between two sequences.
    Lower = more similar.
    """
    if not seq_a and not seq_b:
        return 0.0
    if not seq_a or not seq_b:
        return float("inf")
    a, b = np.array(seq_a), np.array(seq_b)
    n, m = len(a), len(b)
    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])
    return float(dtw[n, m])


class FMG:
    def __init__(self, db_path: str = "fmg.db", fast_path_threshold: float = 0.87):
        self.db_path = db_path
        self.fast_path_threshold = fast_path_threshold
        self._init_db()

    def _init_db(self) -> None:
        try:
            self._create_tables()
        except sqlite3.OperationalError as exc:
            fallback = str(Path(tempfile.gettempdir()) / "sha_fmg.db")
            log.warning(
                "FMG_DB_FALLBACK",
                extra={
                    "request_id": "none",
                    "db_path": self.db_path,
                    "fallback": fallback,
                    "error": str(exc),
                },
            )
            self.db_path = fallback
            self._create_tables()

    def _create_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(CREATE_SIGNATURES)
            conn.execute(CREATE_FIX_ATTEMPTS)

    def store(
        self,
        trajectory: list,
        failure_class: str,
        confidence: float,
        service: str,
        cached_plan: str,
        provenance: str = "SYSTEM_DERIVED",
        request_id: str = "none",
    ) -> str:
        sig_id = str(uuid.uuid4())[:8]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO failure_signatures VALUES (?,?,?,?,?,?,?,?)",
                (
                    sig_id,
                    json.dumps(trajectory),
                    failure_class,
                    confidence,
                    service,
                    cached_plan,
                    provenance,
                    time.time(),
                ),
            )
        log.info(
            "FMG_STORED",
            extra={"request_id": request_id, "sig_id": sig_id, "failure_class": failure_class},
        )
        return sig_id

    def fast_path(
        self,
        trajectory: list,
        service: str,
        request_id: str = "none",
    ) -> Optional[Tuple[str, str, float]]:
        """
        Returns (failure_class, cached_plan, confidence) if a match
        is found above the fast-path threshold. None otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT trajectory, failure_class, cached_plan, confidence "
                "FROM failure_signatures WHERE service = ?",
                (service,),
            ).fetchall()

        best_key = (np.inf, np.inf)
        best_match = None
        for row in rows:
            stored_traj = json.loads(row[0])
            dist = _dtw_distance(trajectory, stored_traj)
            key = (dist, abs(len(stored_traj) - len(trajectory)))
            if key < best_key:
                best_key = key
                best_match = row

        if best_match is None:
            log.info("FMG_NO_MATCH", extra={"request_id": request_id, "service": service})
            return None

        similarity = 1.0 / (1.0 + best_key[0])
        log.info(
            "FMG_MATCH_EVALUATED",
            extra={
                "request_id": request_id,
                "similarity": similarity,
                "threshold": self.fast_path_threshold,
            },
        )

        if similarity >= self.fast_path_threshold:
            log.info(
                "FMG_FAST_PATH_FIRED",
                extra={
                    "request_id": request_id,
                    "similarity": similarity,
                    "failure_class": best_match[1],
                },
            )
            return (best_match[1], best_match[2], best_match[3])
        return None
