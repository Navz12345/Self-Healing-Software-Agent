import json
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, field_validator

from brain.state import BrainDecision, FailureClass, IncidentBundle
from git_context.correlate import extract_suspect_commit
from logger import get_logger

log = get_logger(__name__)
_client: OpenAI | None = None

SYSTEM_PROMPT = """You are a production incident diagnosis system.
You receive: (1) current signal values from monitoring drones,
(2) relevant runbook excerpts retrieved from an operational knowledge base,
(3) recent git commits that may have caused the failure.
You must return ONLY valid JSON matching the schema provided.
Base your diagnosis on the evidence given - do not guess."""


class DiagnosisOutput(BaseModel):
    failure_class: str
    confidence: float
    affected_component: str
    proposed_plan: str
    reasoning: str
    suspect_commit: Optional[str] = None

    @field_validator("failure_class")
    @classmethod
    def valid_class(cls, value: str) -> str:
        allowed = {item.value for item in FailureClass}
        if value not in allowed:
            raise ValueError(f"failure_class must be one of {allowed}")
        return value

    @field_validator("confidence")
    @classmethod
    def valid_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("proposed_plan")
    @classmethod
    def valid_plan(cls, value: str) -> str:
        if value not in {"PLAN_A", "PLAN_B", "PLAN_C"}:
            raise ValueError("proposed_plan must be one of PLAN_A, PLAN_B, PLAN_C")
        return value


def _get_client() -> OpenAI | None:
    global _client
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "sk-your-key-here":
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def _fallback_output(bundle: IncidentBundle) -> DiagnosisOutput:
    signal_values = {signal.signal_type: signal.value for signal in bundle.signals}
    rag_text = "\n".join(bundle.retrieved_chunks).upper()
    suspect = extract_suspect_commit(bundle.recent_commits, request_id=bundle.request_id)

    max_signal = max(signal_values.values(), default=0.0)
    if 0.0 < max_signal < 0.6:
        return DiagnosisOutput(
            failure_class=FailureClass.ANOMALOUS_OUTPUT.value,
            confidence=0.45,
            affected_component=bundle.service,
            proposed_plan="PLAN_C",
            reasoning="Signals are mixed and below the confidence threshold for autonomous repair.",
            suspect_commit=suspect,
        )

    if (
        signal_values.get("error_rate", 0.0) >= 1.0
        and signal_values.get("log_error_density", 0.0) == 0.0
    ):
        return DiagnosisOutput(
            failure_class=FailureClass.INFRA_CRASH.value,
            confidence=0.88,
            affected_component=bundle.service,
            proposed_plan="PLAN_C",
            reasoning="Health checks indicate the service is unreachable without application error logs.",
            suspect_commit=None,
        )

    if "CODE_BUG" in rag_text or signal_values.get("log_error_density", 0.0) > 0.0:
        return DiagnosisOutput(
            failure_class=FailureClass.CODE_BUG.value,
            confidence=0.91,
            affected_component=bundle.service,
            proposed_plan="PLAN_A",
            reasoning="Application error logs and runbook context point to a code bug in transaction logic.",
            suspect_commit=suspect,
        )

    return DiagnosisOutput(
        failure_class=FailureClass.ANOMALOUS_OUTPUT.value,
        confidence=0.45,
        affected_component=bundle.service,
        proposed_plan="PLAN_C",
        reasoning="Signals are mixed and do not identify a safe automated fix.",
        suspect_commit=suspect,
    )


def _is_metric_only_outage(bundle: IncidentBundle) -> bool:
    return bool(bundle.signals) and all(
        signal.signal_type == "error_rate" and signal.value >= 1.0 for signal in bundle.signals
    )


def _decision_from_output(
    bundle: IncidentBundle, parsed: DiagnosisOutput, skipped: bool
) -> BrainDecision:
    if parsed.failure_class == FailureClass.CODE_BUG.value:
        correlated = extract_suspect_commit(bundle.recent_commits, request_id=bundle.request_id)
        if correlated:
            parsed.suspect_commit = correlated

    return BrainDecision(
        request_id=bundle.request_id,
        failure_class=FailureClass(parsed.failure_class),
        confidence=parsed.confidence,
        affected_component=parsed.affected_component,
        proposed_plan=parsed.proposed_plan,
        reasoning=parsed.reasoning,
        suspect_commit=parsed.suspect_commit,
        fmg_match=None,
        gpt4o_skipped=skipped,
        retrieved_chunks=bundle.retrieved_chunks,
    )


def _build_user_message(bundle: IncidentBundle) -> str:
    signal_summary = "\n".join(
        f"- {signal.signal_type}: {signal.value:.3f} (reliability {signal.reliability:.2f})"
        for signal in bundle.signals
    )
    rag_context = "\n\n".join(bundle.retrieved_chunks) or "No runbook context retrieved."
    git_context = bundle.recent_commits or "No recent commits."

    return f"""
## Current Signals
Service: {bundle.service}
{signal_summary}

## Retrieved Runbook Context
{rag_context}

## Recent Git Commits (last 6 hours)
{git_context}

## Required Output Schema
{{
  "failure_class":      one of CODE_BUG|INFRA_CRASH|SCHEMA_VIOLATION|CONFIG_DRIFT|DEPENDENCY_CASCADE|ANOMALOUS_OUTPUT,
  "confidence":         float between 0.0 and 1.0,
  "affected_component": string matching a known service name,
  "proposed_plan":      one of PLAN_A|PLAN_B|PLAN_C,
  "reasoning":          string explaining your diagnosis,
  "suspect_commit":     git hash string if a recent commit is likely the cause, else null
}}
"""


def diagnose(bundle: IncidentBundle) -> BrainDecision:
    user_message = _build_user_message(bundle)

    if _is_metric_only_outage(bundle):
        parsed = _fallback_output(bundle)
        decision = _decision_from_output(bundle, parsed, skipped=True)
        log.info(
            "DIAGNOSIS_COMPLETE",
            extra={
                "request_id": bundle.request_id,
                "failure_class": parsed.failure_class,
                "confidence": parsed.confidence,
                "suspect_commit": parsed.suspect_commit,
                "retrieved_chunks": bundle.retrieved_chunks,
                "fallback": True,
                "deterministic": True,
            },
        )
        return decision

    client = _get_client()

    if client is None:
        parsed = _fallback_output(bundle)
        decision = _decision_from_output(bundle, parsed, skipped=True)
        log.info(
            "DIAGNOSIS_COMPLETE",
            extra={
                "request_id": bundle.request_id,
                "failure_class": parsed.failure_class,
                "confidence": parsed.confidence,
                "suspect_commit": parsed.suspect_commit,
                "retrieved_chunks": bundle.retrieved_chunks,
                "fallback": True,
            },
        )
        return decision

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            content = response.choices[0].message.content or "{}"
            raw = json.loads(content)
            parsed = DiagnosisOutput(**raw)
            decision = _decision_from_output(bundle, parsed, skipped=False)
            log.info(
                "DIAGNOSIS_COMPLETE",
                extra={
                    "request_id": bundle.request_id,
                    "failure_class": parsed.failure_class,
                    "confidence": parsed.confidence,
                    "suspect_commit": parsed.suspect_commit,
                    "retrieved_chunks": bundle.retrieved_chunks,
                    "fallback": False,
                },
            )
            return decision
        except Exception as exc:
            log.error(
                "DIAGNOSIS_FAILED",
                extra={"request_id": bundle.request_id, "attempt": attempt + 1, "error": str(exc)},
            )
            if attempt == 1:
                parsed = _fallback_output(bundle)
                decision = _decision_from_output(bundle, parsed, skipped=True)
                log.info(
                    "DIAGNOSIS_COMPLETE",
                    extra={
                        "request_id": bundle.request_id,
                        "failure_class": parsed.failure_class,
                        "confidence": parsed.confidence,
                        "suspect_commit": parsed.suspect_commit,
                        "retrieved_chunks": bundle.retrieved_chunks,
                        "fallback": True,
                    },
                )
                return decision

    raise RuntimeError("diagnosis did not produce a decision")
