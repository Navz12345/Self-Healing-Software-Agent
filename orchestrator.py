import json
import os

import redis
from langgraph.graph import END, StateGraph

from agents.code_repair import repair
from agents.devops import restart
from agents.validation import validate_and_close
from brain.consensus import ConsensusEngine
from brain.decision import route
from brain.diagnosis import diagnose
from brain.state import BrainDecision, FailureClass, IncidentBundle
from fmg.fmg import FMG
from git_context.correlate import get_recent_commits
from logger import get_logger
from rag.embed import build_collection
from rag.retrieve import retrieve

log = get_logger("orchestrator")
_fmg: FMG | None = None
_collection = None
_consensus: ConsensusEngine | None = None


def get_fmg() -> FMG:
    global _fmg
    if _fmg is None:
        threshold = float(os.getenv("FMG_FAST_PATH_THRESHOLD", "0.87"))
        _fmg = FMG(db_path=os.getenv("FMG_PATH", "fmg.db"), fast_path_threshold=threshold)
    return _fmg


def get_collection():
    global _collection
    if _collection is None:
        _collection = build_collection()
    return _collection


def get_consensus() -> ConsensusEngine:
    global _consensus
    if _consensus is None:
        _consensus = ConsensusEngine(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            window_sec=int(os.getenv("CONSENSUS_WINDOW", "60")),
        )
    return _consensus


def node_check_fmg(state: dict) -> dict:
    """
    Before calling GPT-4o, check if FMG fast-path can handle this.
    If yes, build a BrainDecision from the cached plan and skip diagnosis.
    """
    bundle: IncidentBundle = state["bundle"]
    has_app_log_signal = any(
        signal.signal_type == "log_error_density" and signal.value > 0 for signal in bundle.signals
    )
    if not has_app_log_signal:
        log.info(
            "FMG_SKIPPED",
            extra={
                "request_id": bundle.request_id,
                "reason": "no_application_log_signal",
            },
        )
        return {**state, "fast_path": False}

    match = get_fmg().fast_path(
        bundle.signal_trajectory, bundle.service, request_id=bundle.request_id
    )
    if match:
        failure_class, cached_plan, confidence = match
        decision = BrainDecision(
            request_id=bundle.request_id,
            failure_class=FailureClass(failure_class),
            confidence=confidence,
            affected_component=bundle.service,
            proposed_plan=cached_plan,
            reasoning="FMG fast-path: matched historical fingerprint.",
            suspect_commit=None,
            fmg_match="fast_path",
            gpt4o_skipped=True,
            retrieved_chunks=[],
        )
        log.info("GPT4O_SKIPPED", extra={"request_id": bundle.request_id})
        return {**state, "decision": decision, "fast_path": True}
    return {**state, "fast_path": False}


def node_enrich(state: dict) -> dict:
    """Fetch RAG chunks and git context before diagnosis."""
    bundle: IncidentBundle = state["bundle"]
    query = (
        "error in "
        + bundle.service
        + ": "
        + " ".join(f"{signal.signal_type}={signal.value:.2f}" for signal in bundle.signals)
    )
    chunks = retrieve(query, get_collection(), top_k=2, request_id=bundle.request_id)
    commits = get_recent_commits(request_id=bundle.request_id)
    bundle.retrieved_chunks = chunks
    bundle.recent_commits = commits
    log.info(
        "INCIDENT_ENRICHED",
        extra={"request_id": bundle.request_id, "chunks": len(chunks)},
    )
    return {**state, "bundle": bundle}


def node_diagnose(state: dict) -> dict:
    decision = diagnose(state["bundle"])
    return {**state, "decision": decision}


def node_check_confidence(state: dict) -> dict:
    decision: BrainDecision = state["decision"]
    low = decision.confidence < float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    log.info(
        "CONFIDENCE_CHECKED",
        extra={"request_id": decision.request_id, "confidence": decision.confidence, "low": low},
    )
    return {**state, "low_confidence": low}


def node_escalate(state: dict) -> dict:
    from notify.slack import send_notification

    bundle: IncidentBundle = state["bundle"]
    decision: BrainDecision = state["decision"]
    log.info(
        "ESCALATION_REQUIRED",
        extra={
            "request_id": bundle.request_id,
            "confidence": decision.confidence,
            "reason": "confidence below threshold",
        },
    )
    send_notification(decision, bundle, resolved=False)
    return state


def node_repair(state: dict) -> dict:
    success = repair(state["decision"])
    return {**state, "repair_success": success}


def node_devops(state: dict) -> dict:
    success = restart(state["decision"])
    return {**state, "devops_success": success}


def node_validate(state: dict) -> dict:
    validate_and_close(state["decision"], state["bundle"], fmg=get_fmg())
    return state


def route_after_fmg(state: dict) -> str:
    return "route_plan" if state.get("fast_path") else "enrich"


def route_after_confidence(state: dict) -> str:
    return "escalate" if state.get("low_confidence") else "route_plan"


def route_plan(state: dict) -> str:
    return route(state["decision"])


def build_graph():
    graph = StateGraph(dict)
    graph.add_node("check_fmg", node_check_fmg)
    graph.add_node("enrich", node_enrich)
    graph.add_node("diagnose", node_diagnose)
    graph.add_node("check_confidence", node_check_confidence)
    graph.add_node("escalate", node_escalate)
    graph.add_node("route_plan", lambda state: state)
    graph.add_node("repair", node_repair)
    graph.add_node("devops", node_devops)
    graph.add_node("validate", node_validate)

    graph.set_entry_point("check_fmg")
    graph.add_conditional_edges(
        "check_fmg", route_after_fmg, {"route_plan": "route_plan", "enrich": "enrich"}
    )
    graph.add_edge("enrich", "diagnose")
    graph.add_edge("diagnose", "check_confidence")
    graph.add_conditional_edges(
        "check_confidence",
        route_after_confidence,
        {"escalate": "escalate", "route_plan": "route_plan"},
    )
    graph.add_edge("escalate", END)
    graph.add_conditional_edges("route_plan", route_plan, {"repair": "repair", "devops": "devops"})
    graph.add_edge("repair", "validate")
    graph.add_edge("devops", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


def main() -> None:
    log.info("ORCHESTRATOR_STARTED", extra={"request_id": "none"})
    graph = build_graph()
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    pubsub = redis_client.pubsub()
    pubsub.subscribe("tier1.alerts")
    consensus = get_consensus()

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        raw = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
        try:
            signal_data = json.loads(raw)
            log.info(
                "SIGNAL_PUBLISHED",
                extra={
                    "request_id": signal_data.get("request_id", "none"),
                    "signal_type": signal_data.get("signal_type"),
                    "value": signal_data.get("value"),
                },
            )
        except Exception:
            log.warning("SIGNAL_DECODE_FAILED", extra={"request_id": "none"})
        bundle = consensus.ingest(raw)
        if bundle is None:
            continue
        log.info(
            "INCIDENT_STARTED",
            extra={"request_id": bundle.request_id, "service": bundle.service},
        )
        try:
            graph.invoke(
                {
                    "bundle": bundle,
                    "decision": None,
                    "fast_path": False,
                    "low_confidence": False,
                }
            )
        except Exception as exc:
            log.error(
                "ORCHESTRATOR_ERROR", extra={"request_id": bundle.request_id, "error": str(exc)}
            )


if __name__ == "__main__":
    main()
