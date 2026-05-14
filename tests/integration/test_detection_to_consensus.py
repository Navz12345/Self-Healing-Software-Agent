from brain.consensus import ConsensusEngine
from monitoring.base_drone import BaseDrone


class FakeRedis:
    def __init__(self):
        self.messages = []

    def publish(self, channel, payload):
        self.messages.append((channel, payload))


class FakeDrone(BaseDrone):
    def signal_type(self) -> str:
        return "error_rate"

    def read(self) -> float:
        return 1.0


def test_detection_signal_can_flow_to_consensus(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr("redis.from_url", lambda _: fake_redis)
    drone = FakeDrone("metric_drone", "sha-app", "redis://localhost:6379")
    drone.publish(1.0, "flow1234")
    drone.publish(1.0, "flow1234")
    drone.publish(1.0, "flow1234")
    drone.publish(1.0, "flow1234")
    engine = ConsensusEngine("redis://localhost:6379")
    bundle = None
    for msg in fake_redis.messages:
        bundle = engine.ingest(msg[1])
        if bundle is not None:
            break
    assert bundle is not None
    assert bundle.request_id == "flow1234"
