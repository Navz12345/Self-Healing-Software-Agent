import requests

from logger import get_logger
from monitoring.base_drone import BaseDrone

log = get_logger(__name__)


class MetricDrone(BaseDrone):
    def __init__(self, health_url: str, **kwargs):
        super().__init__(drone_id="metric_drone", **kwargs)
        self.health_url = health_url
        self._prev_error = 0.0
        log.info("METRIC_DRONE_CONFIGURED", extra={"request_id": "none", "health_url": health_url})

    def signal_type(self) -> str:
        return "error_rate"

    def read(self) -> float:
        try:
            resp = requests.get(self.health_url, timeout=3)
            if resp.status_code != 200:
                log.warning(
                    "HEALTH_STATUS_ERROR",
                    extra={"request_id": "none", "status_code": resp.status_code},
                )
                return 1.0
            data = resp.json()
            value = float(data.get("error_rate", 0.0))
            if value > 0:
                log.info("ERROR_RATE_READ", extra={"request_id": "none", "value": value})
            return value
        except Exception as exc:
            log.warning("HEALTH_UNREACHABLE", extra={"request_id": "none", "error": str(exc)})
            return 1.0
