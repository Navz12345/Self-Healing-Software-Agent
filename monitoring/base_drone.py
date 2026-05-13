import json
import math
import time
import uuid
from collections import deque
from dataclasses import asdict

import redis
from scipy import stats

from brain.state import Signal
from logger import get_logger


class BaseDrone:
    def __init__(
        self,
        drone_id: str,
        service: str,
        redis_url: str,
        poll_interval: int = 5,
        baseline_window: int = 120,
    ):
        self.drone_id = drone_id
        self.service = service
        self.redis_url = redis_url
        self.poll_interval = poll_interval
        self.baseline: deque[float] = deque(maxlen=baseline_window)
        self.redis_client = redis.from_url(redis_url)
        self.log = get_logger(drone_id)

    def read(self) -> float:
        """Override in subclass. Returns the current signal value."""
        raise NotImplementedError

    def signal_type(self) -> str:
        """Override in subclass. Returns signal type string."""
        raise NotImplementedError

    def zscore(self, value: float) -> float:
        if len(self.baseline) < 10:
            return 0.0
        score = float(stats.zscore(list(self.baseline) + [value])[-1])
        if math.isnan(score):
            return 0.0
        return score

    def reliability(self) -> float:
        """
        Simple reliability: 1.0 if readings have been stable and fresh.
        Drops toward 0.0 if consecutive identical readings (stale source).
        """
        if len(self.baseline) < 3:
            return 1.0
        recent = list(self.baseline)[-3:]
        if len(set(recent)) == 1:
            return 0.5
        return 1.0

    def publish(self, value: float, request_id: str) -> None:
        signal = Signal(
            drone_id=self.drone_id,
            service=self.service,
            signal_type=self.signal_type(),
            value=value,
            reliability=self.reliability(),
            timestamp=time.time(),
            request_id=request_id,
        )
        self.redis_client.publish("tier1.alerts", json.dumps(asdict(signal)))
        self.log.info(
            "SIGNAL_PUBLISHED",
            extra={
                "request_id": request_id,
                "signal_type": self.signal_type(),
                "value": value,
                "zscore": self.zscore(value),
            },
        )

    def run(self) -> None:
        self.log.info("DRONE_STARTED", extra={"request_id": "none"})
        while True:
            try:
                value = self.read()
                self.baseline.append(value)
                z = self.zscore(value)
                if z > 2.0 or value > 0.0:
                    rid = str(uuid.uuid4())[:8]
                    self.publish(value, rid)
            except Exception as exc:
                self.log.error("DRONE_ERROR", extra={"request_id": "none", "error": str(exc)})
            time.sleep(self.poll_interval)
