from pathlib import Path

import requests

from monitoring.log_drone import LogDrone
from monitoring.metric_drone import MetricDrone


class FakeRedis:
    def publish(self, *_):
        return None


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_log_drone_reads_only_new_lines(tmp_path, monkeypatch):
    monkeypatch.setattr("redis.from_url", lambda _: FakeRedis())
    log_file = Path(tmp_path) / "app.log"
    log_file.write_text("ERROR old failure\n", encoding="utf-8")

    drone = LogDrone(
        log_file=str(log_file),
        service="sha-app",
        redis_url="redis://localhost:6379",
    )

    assert drone.read() == 0.0

    log_file.write_text(
        "ERROR old failure\nINFO recovered\nERROR fresh failure\n",
        encoding="utf-8",
    )

    assert drone.read() == 0.5
    assert drone.read() == 0.0

    log_file.write_text("", encoding="utf-8")
    assert drone.read() == 0.0


def test_metric_drone_reads_health_and_failures(monkeypatch):
    monkeypatch.setattr("redis.from_url", lambda _: FakeRedis())
    responses = [
        FakeResponse(200, {"error_rate": 0.25}),
        FakeResponse(503, {}),
        requests.Timeout("timed out"),
    ]

    def fake_get(*_, **__):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("requests.get", fake_get)
    drone = MetricDrone(
        health_url="http://sha-app:8000/health",
        service="sha-app",
        redis_url="redis://localhost:6379",
    )

    assert drone.read() == 0.25
    assert drone.read() == 1.0
    assert drone.read() == 1.0
