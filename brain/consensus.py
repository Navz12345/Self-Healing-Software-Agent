import json
import time
from collections import defaultdict
from typing import Dict, List

import redis

from brain.state import IncidentBundle, Signal
from logger import get_logger

log = get_logger(__name__)


class ConsensusEngine:
    def __init__(
        self,
        redis_url: str,
        window_sec: int = 60,
        threshold: float = 1.5,
        min_signal_types: int = 2,
    ):
        self.redis_client = redis.from_url(redis_url)
        self.window_sec = window_sec
        self.threshold = threshold
        self.min_signal_types = min_signal_types
        self.window: Dict[str, List[Signal]] = defaultdict(list)
        log.info(
            "CONSENSUS_ENGINE_STARTED",
            extra={
                "request_id": "none",
                "window_sec": window_sec,
                "threshold": threshold,
                "min_signal_types": min_signal_types,
            },
        )

    def _prune(self) -> None:
        """Remove signals older than window_sec."""
        cutoff = time.time() - self.window_sec
        for service in list(self.window.keys()):
            self.window[service] = [
                signal for signal in self.window[service] if signal.timestamp > cutoff
            ]

    def _weighted_vote(self, signals: List[Signal]) -> float:
        """Sum reliability scores of distinct signal types."""
        seen_types: dict[str, float] = {}
        for signal in signals:
            if (
                signal.signal_type not in seen_types
                or signal.reliability > seen_types[signal.signal_type]
            ):
                seen_types[signal.signal_type] = signal.reliability
        return sum(seen_types.values())

    def ingest(self, raw: str) -> IncidentBundle | None:
        """
        Called for each Redis message.
        Returns an IncidentBundle if consensus threshold is crossed,
        None otherwise.
        """
        data = json.loads(raw)
        signal = Signal(**data)
        self.window[signal.service].append(signal)
        self._prune()

        svc_signals = self.window[signal.service]
        distinct_types = len({item.signal_type for item in svc_signals})
        vote = self._weighted_vote(svc_signals)

        log.info(
            "CONSENSUS_TICK",
            extra={
                "request_id": signal.request_id,
                "service": signal.service,
                "distinct_types": distinct_types,
                "vote": vote,
                "threshold": self.threshold,
            },
        )

        infra_signal_count = sum(
            1 for item in svc_signals if item.signal_type == "error_rate" and item.value >= 1.0
        )
        ambiguous_single_signal = any(
            item.signal_type == "error_rate" and 0.0 < item.value < 0.6 for item in svc_signals
        )
        if (
            (distinct_types >= self.min_signal_types and vote >= self.threshold)
            or infra_signal_count >= 2
            or ambiguous_single_signal
        ):
            log.info(
                "CONSENSUS_REACHED",
                extra={"request_id": signal.request_id, "service": signal.service, "vote": vote},
            )
            trajectory = [
                item.value for item in sorted(svc_signals, key=lambda item: item.timestamp)
            ][-12:]
            bundle = IncidentBundle(
                request_id=signal.request_id,
                service=signal.service,
                signals=svc_signals,
                signal_trajectory=trajectory,
                recent_commits="",
                retrieved_chunks=[],
                weighted_vote=vote,
                timestamp=time.time(),
            )
            self.window[signal.service] = []
            return bundle
        return None
