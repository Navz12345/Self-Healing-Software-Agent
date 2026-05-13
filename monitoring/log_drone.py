from pathlib import Path

from logger import get_logger
from monitoring.base_drone import BaseDrone

log = get_logger(__name__)


class LogDrone(BaseDrone):
    def __init__(self, log_file: str, **kwargs):
        super().__init__(drone_id="log_drone", **kwargs)
        self.log_file = log_file
        self._position = self._initial_position()
        log.info("LOG_DRONE_CONFIGURED", extra={"request_id": "none", "log_file": log_file})

    def _initial_position(self) -> int:
        path = Path(self.log_file)
        if not path.exists():
            return 0
        return path.stat().st_size

    def signal_type(self) -> str:
        return "log_error_density"

    def read(self) -> float:
        path = Path(self.log_file)
        if not path.exists():
            return 0.0

        size = path.stat().st_size
        if size < self._position:
            self._position = 0

        with path.open("r", encoding="utf-8") as handle:
            handle.seek(self._position)
            lines = handle.read().splitlines()
            self._position = handle.tell()

        if not lines:
            return 0.0
        error_count = sum(1 for line in lines if "ERROR" in line)
        value = error_count / len(lines)
        if value > 0:
            log.info(
                "LOG_ERROR_DENSITY_READ",
                extra={"request_id": "none", "value": value, "errors": error_count},
            )
        return value
