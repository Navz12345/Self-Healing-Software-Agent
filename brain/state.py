import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from logger import get_logger

log = get_logger(__name__)


class FailureClass(str, Enum):
    CODE_BUG = "CODE_BUG"
    INFRA_CRASH = "INFRA_CRASH"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    CONFIG_DRIFT = "CONFIG_DRIFT"
    DEPENDENCY_CASCADE = "DEPENDENCY_CASCADE"
    ANOMALOUS_OUTPUT = "ANOMALOUS_OUTPUT"


@dataclass
class Signal:
    drone_id: str
    service: str
    signal_type: str
    value: float
    reliability: float
    timestamp: float
    request_id: str


@dataclass
class IncidentBundle:
    request_id: str
    service: str
    signals: List[Signal]
    signal_trajectory: List[float]
    recent_commits: str
    retrieved_chunks: List[str]
    weighted_vote: float
    timestamp: float


@dataclass
class BrainDecision:
    request_id: str
    failure_class: FailureClass
    confidence: float
    affected_component: str
    proposed_plan: str
    reasoning: str
    suspect_commit: Optional[str]
    fmg_match: Optional[str]
    gpt4o_skipped: bool
    retrieved_chunks: List[str] = field(default_factory=list)


def new_incident_timestamp() -> float:
    now = time.time()
    log.info("INCIDENT_TIMESTAMP_CREATED", extra={"request_id": "none", "timestamp": now})
    return now
