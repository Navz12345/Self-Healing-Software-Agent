import time

import orchestrator
from brain.state import BrainDecision, FailureClass, IncidentBundle, Signal


def make_bundle() -> IncidentBundle:
    now = time.time()
    return IncidentBundle(
        "orch1",
        "sha-app",
        [
            Signal("metric_drone", "sha-app", "error_rate", 1.0, 1.0, now, "orch1"),
            Signal("log_drone", "sha-app", "log_error_density", 1.0, 1.0, now, "orch1"),
        ],
        [1.0, 1.0],
        "",
        [],
        2.0,
        now,
    )


def make_decision() -> BrainDecision:
    return BrainDecision(
        "orch1", FailureClass.CODE_BUG, 0.9, "sha-app", "PLAN_A", "repair", None, None, False, []
    )


class FakeFMG:
    def fast_path(self, trajectory, service, request_id="none"):
        return ("CODE_BUG", "PLAN_A", 0.91)


def test_node_check_fmg_fast_path(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_fmg", lambda: FakeFMG())

    state = orchestrator.node_check_fmg({"bundle": make_bundle()})

    assert state["fast_path"] is True
    assert state["decision"].gpt4o_skipped is True


def test_node_enrich_adds_rag_and_commits(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_collection", lambda: object())
    monkeypatch.setattr(orchestrator, "retrieve", lambda *_, **__: ["chunk"])
    monkeypatch.setattr(orchestrator, "get_recent_commits", lambda **_: "abc1234 msg")

    state = orchestrator.node_enrich({"bundle": make_bundle()})

    assert state["bundle"].retrieved_chunks == ["chunk"]
    assert "abc1234" in state["bundle"].recent_commits


def test_orchestrator_action_nodes(monkeypatch):
    decision = make_decision()
    bundle = make_bundle()
    state = {"decision": decision, "bundle": bundle}
    monkeypatch.setattr(orchestrator, "repair", lambda _: True)
    monkeypatch.setattr(orchestrator, "restart", lambda _: True)
    monkeypatch.setattr(orchestrator, "validate_and_close", lambda *_, **__: True)
    monkeypatch.setattr(orchestrator, "get_fmg", lambda: None)

    assert orchestrator.node_repair(state)["repair_success"] is True
    assert orchestrator.node_devops(state)["devops_success"] is True
    assert orchestrator.node_validate(state) == state
    assert orchestrator.route_after_fmg({"fast_path": True}) == "route_plan"
    assert orchestrator.route_after_confidence({"low_confidence": True}) == "escalate"
    assert orchestrator.route_plan({"decision": decision}) == "repair"


def test_build_graph_compiles():
    assert orchestrator.build_graph() is not None
