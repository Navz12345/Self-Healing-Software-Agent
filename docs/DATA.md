# Data Card

## Inputs

The system consumes only local demo telemetry produced by the Docker Compose stack.

Application logs are converted into JSON signal messages and published on Redis channel `tier1.alerts`. The log drone tails `app/app.log`, computes `log_error_density`, and publishes a typed signal with service name, signal type, numeric value, reliability, timestamp, and request ID.

Metric signals are also published as JSON on Redis channel `tier1.alerts`. The metric drone polls the `sha-app` health endpoint and emits `error_rate`.

Signal values are floats in the range `0.0` to `1.0`:

- `error_rate`: `0.0` means the health endpoint reports no errors; `1.0` means the service is unreachable or unhealthy.
- `log_error_density`: `0.0` means no new error lines were found; `1.0` means all newly read log lines were errors.

The incident signal schema is:

```json
{
  "drone_id": "metric_drone",
  "service": "sha-app",
  "signal_type": "error_rate",
  "value": 1.0,
  "reliability": 1.0,
  "timestamp": 1710000000.0,
  "request_id": "abc12345"
}
```

## Internal Storage

FMG fingerprints are stored in SQLite database `fmg.db`, table `failure_signatures`.

The `failure_signatures` table stores:

- `id`
- `trajectory`
- `failure_class`
- `confidence`
- `service`
- `cached_plan`
- `provenance`
- `created_at`

RAG embeddings are stored in ChromaDB at `.chromadb/`. The collection is seeded from local runbook chunks in `rag/runbook.md`.

Incident state is held in Redis during runtime. Redis carries drone signal messages on `tier1.alerts`; the orchestrator consumes those messages and builds in-memory `IncidentBundle` state during consensus and graph execution.

## Outputs

For code repair stories, the system promotes patched `payments.py` files to:

- `app/payments.py`
- `sandbox_app/payments.py`

The sandbox copy is written first and tested before the production app copy is promoted.

Slack notifications are sent through the configured Slack incoming webhook. The Slack webhook JSON payload contains the incident status and block fields for:

- `failure_class`
- `confidence`
- `suspect_commit`
- resolved status

When Slack is not configured, the system still logs `SLACK_SENT` with `configured=false` so evaluators can trace notification behavior.

## Privacy

No personal data is collected or stored. The system uses synthetic demo failures, service health metrics, local application logs, local git commit summaries, local runbook text, and generated incident IDs.

No user profile, customer record, credential, payment card, email inbox, chat history, or other personal dataset is ingested by the MVP.

## Retention

All runtime data is ephemeral and is intended for local demo use.

Runtime data is lost on:

```powershell
docker compose down -v
```

This removes Docker volumes and clears Redis state. Local runtime artifacts such as `fmg.db`, `.chromadb/`, and generated logs may also be deleted between demo sessions when a clean state is required.
