# Incident Summary Report

Generated from live demo runs on 2026-05-13.

## Incident 1 — US-01: Autonomous Code Bug Repair

| Field | Value |
|-------|-------|
| Request ID | 9f5b5bfb |
| Failure Class | CODE_BUG |
| Confidence | 0.95 |
| Suspect Commit | 00cf52f refactor: optimize transaction calculation |
| Diagnosis Path | GPT-4o (real inference, fallback=false) |
| RAG Chunks Retrieved | 2 |
| Sandbox Result | PASSED (1 test in 0.59s) |
| Repair Action | PATCH_PROMOTED |
| Health Confirmed | attempt=1 |
| Slack Notification | status_code=200 resolved=true |
| Detection to Resolution | ~13 seconds |

### Event Timeline
| Timestamp | Event |
|-----------|-------|
| 04:36:28 | SIGNAL_PUBLISHED log_error_density=1.0 |
| 04:36:30 | SIGNAL_PUBLISHED error_rate=1.0 |
| 04:36:30 | CONSENSUS_REACHED vote=2.0 |
| 04:36:30 | INCIDENT_STARTED |
| 04:36:30 | FMG_NO_MATCH (fresh fingerprint) |
| 04:36:30 | RAG_RETRIEVED chunks_returned=2 |
| 04:36:30 | GIT_COMMITS_FETCHED commit_count=1 |
| 04:36:33 | SUSPECT_COMMIT_FOUND 00cf52f |
| 04:36:33 | DIAGNOSIS_COMPLETE CODE_BUG confidence=0.95 |
| 04:36:33 | DECISION_ROUTE_CODE_REPAIR PLAN_A |
| 04:36:35 | SANDBOX_PATCH_WRITTEN |
| 04:36:37 | SANDBOX_RESULT passed=true |
| 04:36:38 | PATCH_PROMOTED |
| 04:36:43 | HEALTH_CONFIRMED attempt=1 |
| 04:36:44 | FMG_STORED sig_id=896aed76 |
| 04:36:44 | SLACK_SENT status_code=200 resolved=true |

---

## Incident 2 — US-02: Infrastructure Crash Recovery

| Field | Value |
|-------|-------|
| Request ID | 5c15f0f0 |
| Failure Class | INFRA_CRASH |
| Confidence | 0.88 |
| Diagnosis Path | Deterministic guard (metric-only bundle) |
| Repair Action | CONTAINER_RESTARTED attempts=1 |
| Health Confirmed | attempt=1 |
| Slack Notification | status_code=200 resolved=true |
| Detection to Resolution | ~11 seconds |

### Event Timeline
| Timestamp | Event |
|-----------|-------|
| 04:05:22 | CONSENSUS_REACHED vote=1.0 |
| 04:05:22 | INCIDENT_STARTED |
| 04:05:22 | FMG_SKIPPED reason=no_application_log_signal |
| 04:05:23 | DIAGNOSIS_COMPLETE INFRA_CRASH confidence=0.88 deterministic=true |
| 04:05:23 | DECISION_ROUTE_DEVOPS PLAN_C |
| 04:05:23 | DEVOPS_RESTART container=sha-app |
| 04:05:28 | CONTAINER_RESTARTED attempts=1 |
| 04:05:33 | HEALTH_CONFIRMED attempt=1 |
| 04:05:34 | SLACK_SENT status_code=200 resolved=true |

---

## Incident 3 — US-03: FMG Fast-Path Learning

| Field | Value |
|-------|-------|
| Request ID | e428feb6 |
| Failure Class | CODE_BUG |
| FMG Similarity | 1.0 (exact match) |
| Diagnosis Path | FMG_FAST_PATH_FIRED — GPT4O_SKIPPED |
| Repair Action | PATCH_PROMOTED |
| Health Confirmed | attempt=1 |
| Slack Notification | status_code=200 resolved=true |
| FMG to Resolution | 11 seconds |

### Event Timeline
| Timestamp | Event |
|-----------|-------|
| 04:03:56 | CONSENSUS_REACHED vote=2.0 |
| 04:03:56 | FMG_MATCH_EVALUATED similarity=1.0 |
| 04:03:56 | FMG_FAST_PATH_FIRED failure_class=CODE_BUG |
| 04:03:56 | GPT4O_SKIPPED |
| 04:03:56 | DECISION_ROUTE_CODE_REPAIR PLAN_A |
| 04:04:01 | SANDBOX_RESULT passed=true |
| 04:04:02 | PATCH_PROMOTED |
| 04:04:07 | HEALTH_CONFIRMED attempt=1 |
| 04:04:07 | SLACK_SENT status_code=200 resolved=true |

---

## Incident 4 — US-04: Low Confidence Escalation

| Field | Value |
|-------|-------|
| Request ID | fea425b3 |
| Failure Class | ANOMALOUS_OUTPUT |
| Confidence | 0.55 (below 0.60 threshold) |
| Diagnosis Path | GPT-4o (real inference) |
| Repair Action | NONE — escalated to human |
| Slack Notification | status_code=200 resolved=false |
| App Health After | ok (no patch applied) |

### Event Timeline
| Timestamp | Event |
|-----------|-------|
| 05:31:14 | CONSENSUS_REACHED |
| 05:31:19 | DIAGNOSIS_COMPLETE ANOMALOUS_OUTPUT confidence=0.55 |
| 05:31:19 | CONFIDENCE_CHECKED low=true |
| 05:31:19 | ESCALATION_REQUIRED reason=confidence below threshold |
| 05:31:19 | SLACK_SENT status_code=200 resolved=false |

---

## Summary

| Story | Failure Class | Confidence | Repair | MTTR | Result |
|-------|--------------|------------|--------|------|--------|
| US-01 | CODE_BUG | 0.95 | PATCH_PROMOTED | 13s | RESOLVED |
| US-02 | INFRA_CRASH | 0.88 | CONTAINER_RESTARTED | 11s | RESOLVED |
| US-03 | CODE_BUG | FMG | PATCH_PROMOTED | 11s | RESOLVED |
| US-04 | ANOMALOUS_OUTPUT | 0.55 | ESCALATED | N/A | ESCALATED |
| US-05 | CODE_BUG | 0.95 | RAG verified | 13s | RESOLVED |

All Slack notifications delivered with HTTP 200.
GPT-4o real inference confirmed (fallback=false) on US-01 and US-05.
FMG fast-path confirmed (similarity=1.0) on US-03.
