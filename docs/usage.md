# Usage Guide

This guide assumes Docker Desktop is running and the stack has already been started with:

```powershell
docker compose up
```

Use a second PowerShell terminal for the commands below. To inspect orchestrator logs at any time, run:

```powershell
docker compose logs orchestrator
```

## US-01: Divide-By-Zero Autonomous Repair

What the story tests: the system detects a code bug, diagnoses it as `CODE_BUG`, repairs `payments.py`, validates health, and sends a Slack trace.

Exact command to run:

```powershell
python inject_failure.py --type divide_by_zero
```

Exact log events to look for in `docker compose logs orchestrator`:

```text
CONSENSUS_REACHED
DIAGNOSIS_COMPLETE
CODE_BUG
PATCH_PROMOTED
HEALTH_CONFIRMED
SLACK_SENT
```

`REVERT_PROMOTED` is also acceptable in place of `PATCH_PROMOTED` when the system safely reverts the suspect commit.

Verification command:

```powershell
curl.exe http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```

Additional verification:

```powershell
docker compose logs orchestrator | Select-String "DIAGNOSIS_COMPLETE|CODE_BUG|PATCH_PROMOTED|REVERT_PROMOTED|HEALTH_CONFIRMED|SLACK_SENT"
```

What failure looks like:

- `CONSENSUS_REACHED` never appears: the drones are not publishing signals or Redis is unavailable.
- `DIAGNOSIS_COMPLETE` appears without `CODE_BUG`: diagnosis did not identify the code bug.
- Neither `PATCH_PROMOTED` nor `REVERT_PROMOTED` appears: repair did not pass sandbox validation or could not be promoted.
- `HEALTH_CONFIRMED` never appears: the app did not recover after repair.
- `SLACK_SENT` never appears: notification tracing is broken, even if Slack is not configured.

## US-02: Infrastructure Crash Recovery

What the story tests: the system detects that `sha-app` is unreachable, diagnoses `INFRA_CRASH`, restarts the container, and validates recovery.

Exact command to run:

```powershell
python inject_failure.py --type infra_crash
```

Exact log events to look for in `docker compose logs orchestrator`:

```text
CONSENSUS_REACHED
DIAGNOSIS_COMPLETE
INFRA_CRASH
DEVOPS_RESTART
CONTAINER_RESTARTED
HEALTH_CONFIRMED
```

Verification command:

```powershell
curl.exe http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```

Additional verification:

```powershell
docker compose logs orchestrator | Select-String "DIAGNOSIS_COMPLETE|INFRA_CRASH|DEVOPS_RESTART|CONTAINER_RESTARTED|HEALTH_CONFIRMED"
```

What failure looks like:

- `CONSENSUS_REACHED` never appears: metric signals are not reaching Redis.
- `DIAGNOSIS_COMPLETE` appears without `INFRA_CRASH`: the outage was not classified correctly.
- `DOCKER_CLI_UNAVAILABLE`, `RESTART_FAILED`, or `HEALTH_NOT_RESTORED` appears: the orchestrator could not restart or validate `sha-app`.
- `curl.exe http://localhost:8000/health` fails or does not return `status` as `ok`: recovery did not complete.

## US-03: FMG Fast-Path Learning

What the story tests: after a successful previous repair, FMG recognizes the repeated signal trajectory and skips GPT-4o.

Prerequisite: run `US-01` successfully in the same Docker session before this story.

Exact command to run:

```powershell
python inject_failure.py --type divide_by_zero
```

Exact log events to look for in `docker compose logs orchestrator`:

```text
FMG_FAST_PATH_FIRED
GPT4O_SKIPPED
PATCH_PROMOTED
HEALTH_CONFIRMED
```

`REVERT_PROMOTED` is also acceptable in place of `PATCH_PROMOTED`.

Verification command:

```powershell
docker compose exec orchestrator sqlite3 fmg.db "SELECT COUNT(*) FROM failure_signatures"
```

Expected output:

```text
1
```

Any integer greater than or equal to `1` is acceptable.

Speed verification command:

```powershell
docker compose logs orchestrator | Select-String "FMG_FAST_PATH_FIRED|HEALTH_CONFIRMED"
```

Expected output:

- A `FMG_FAST_PATH_FIRED` log line and a later `HEALTH_CONFIRMED` log line for the same `request_id`.
- The timestamp difference between those two lines is under 20 seconds.

What failure looks like:

- The FMG count is `0`: `US-01` did not store a fingerprint or FMG was cleared.
- `FMG_FAST_PATH_FIRED` never appears: the repeated trajectory did not match the stored fingerprint.
- `GPT4O_SKIPPED` never appears: the fast path did not bypass model diagnosis.
- `DIAGNOSIS_COMPLETE` appears before fast-path routing for the same request: the request went through GPT-4o instead of FMG.
- `HEALTH_CONFIRMED` occurs more than 20 seconds after `FMG_FAST_PATH_FIRED`: the fast-path latency requirement failed.

## US-04: Low-Confidence Escalation

What the story tests: ambiguous failures below the confidence threshold are escalated instead of repaired or restarted.

Exact command to run:

```powershell
python inject_failure.py --type ambiguous
```

Exact log events to look for in `docker compose logs orchestrator`:

```text
CONSENSUS_REACHED
DIAGNOSIS_COMPLETE
ESCALATION_REQUIRED
SLACK_SENT
```

The `DIAGNOSIS_COMPLETE` line must show confidence below `0.60`. The `SLACK_SENT` line must show `resolved` as `false`.

Verification command:

```powershell
curl.exe http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```

Additional verification commands:

```powershell
docker compose logs orchestrator | Select-String "ESCALATION_REQUIRED|SLACK_SENT"
docker compose logs orchestrator | Select-String "PATCH_PROMOTED|CONTAINER_RESTARTED"
```

Expected output:

- The first command shows escalation and Slack trace lines for the ambiguous request.
- The second command shows no new `PATCH_PROMOTED` or `CONTAINER_RESTARTED` lines for the ambiguous request ID.

What failure looks like:

- `DIAGNOSIS_COMPLETE` shows confidence `0.60` or higher: the incident should not have been considered low confidence.
- `ESCALATION_REQUIRED` never appears: the low-confidence path did not run.
- `PATCH_PROMOTED` appears for the ambiguous request ID: the system incorrectly attempted code repair.
- `CONTAINER_RESTARTED` appears for the ambiguous request ID: the system incorrectly attempted infrastructure recovery.
- `SLACK_SENT` does not appear with `resolved=false`: escalation notification tracing failed.

## US-05: RAG-Augmented Diagnosis Verification

What the story tests: diagnosis includes non-empty runbook chunks retrieved from ChromaDB.

Exact command to run:

```powershell
python inject_failure.py --type divide_by_zero
```

Exact log events to look for in `docker compose logs orchestrator`:

```text
RAG_RETRIEVED
INCIDENT_ENRICHED
DIAGNOSIS_COMPLETE
retrieved_chunks
CODE_BUG
```

Verification command:

```powershell
docker compose logs orchestrator | Select-String "retrieved_chunks"
```

Expected output:

- At least one `DIAGNOSIS_COMPLETE` log line contains `"retrieved_chunks": [` with one or more non-empty strings.
- The chunk text includes content from `rag/runbook.md`, such as `CODE_BUG`, `ZeroDivisionError`, or divide-by-zero guidance.

Additional verification command:

```powershell
docker compose logs orchestrator | Select-String "CODE_BUG|ZeroDivisionError|divide-by-zero"
```

Expected output:

- At least one matching line appears in the diagnosis or retrieval logs.

What failure looks like:

- `RAG_RETRIEVED` never appears: retrieval did not run.
- `INCIDENT_ENRICHED` never appears: the orchestrator did not attach RAG and git context before diagnosis.
- `retrieved_chunks` is missing from `DIAGNOSIS_COMPLETE`: diagnosis logs are incomplete.
- `retrieved_chunks` is an empty list: ChromaDB was not seeded or retrieval returned no context.
- Retrieved chunks do not contain runbook text: the RAG collection is stale or seeded from the wrong source.
