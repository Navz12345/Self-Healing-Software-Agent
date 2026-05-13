import json
import time

from brain.consensus import ConsensusEngine


def test_consensus_reaches_bundle_with_two_signal_types():
    engine = ConsensusEngine("redis://localhost:6379")
    first = {
        "drone_id": "log_drone",
        "service": "sha-app",
        "signal_type": "log_error_density",
        "value": 0.8,
        "reliability": 0.9,
        "timestamp": time.time(),
        "request_id": "abc12345",
    }
    second = {
        "drone_id": "metric_drone",
        "service": "sha-app",
        "signal_type": "error_rate",
        "value": 1.0,
        "reliability": 0.8,
        "timestamp": time.time(),
        "request_id": "abc12345",
    }

    assert engine.ingest(json.dumps(first)) is None
    bundle = engine.ingest(json.dumps(second))

    assert bundle is not None
    assert bundle.request_id == "abc12345"
    assert bundle.weighted_vote >= 1.5
