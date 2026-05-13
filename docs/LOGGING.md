# Logging

All modules use `get_logger` from `logger.py`. Every log entry is a JSON object with `timestamp`, `level`, `module`, `request_id`, and `message`. The `request_id` field propagates through every component that handles the same incident.

## Example Trace

The following is a real captured trace from request `9f5b5bfb` during a divide-by-zero demo run:

```json
{"timestamp":"2026-05-13T04:36:30","level":"INFO","module":"orchestrator","request_id":"9f5b5bfb","message":"SIGNAL_PUBLISHED","signal_type":"error_rate","value":1.0}
{"timestamp":"2026-05-13T04:36:30","level":"INFO","module":"consensus","request_id":"9f5b5bfb","message":"CONSENSUS_REACHED","service":"sha-app","vote":2.0}
{"timestamp":"2026-05-13T04:36:30","level":"INFO","module":"orchestrator","request_id":"9f5b5bfb","message":"INCIDENT_STARTED","service":"sha-app"}
{"timestamp":"2026-05-13T04:36:30","level":"INFO","module":"retrieve","request_id":"9f5b5bfb","message":"RAG_RETRIEVED","chunks_returned":2}
{"timestamp":"2026-05-13T04:36:33","level":"INFO","module":"diagnosis","request_id":"9f5b5bfb","message":"DIAGNOSIS_COMPLETE","failure_class":"CODE_BUG","confidence":0.95}
{"timestamp":"2026-05-13T04:36:33","level":"INFO","module":"decision","request_id":"9f5b5bfb","message":"DECISION_ROUTE_CODE_REPAIR","plan":"PLAN_A"}
{"timestamp":"2026-05-13T04:36:37","level":"INFO","module":"code_repair","request_id":"9f5b5bfb","message":"SANDBOX_RESULT","passed":true}
{"timestamp":"2026-05-13T04:36:38","level":"INFO","module":"code_repair","request_id":"9f5b5bfb","message":"PATCH_PROMOTED"}
{"timestamp":"2026-05-13T04:36:43","level":"INFO","module":"validation","request_id":"9f5b5bfb","message":"HEALTH_CONFIRMED","attempt":1}
{"timestamp":"2026-05-13T04:36:44","level":"INFO","module":"slack","request_id":"9f5b5bfb","message":"SLACK_SENT","status_code":200,"resolved":true}
```

## How to Trace a Live Request

```powershell
docker compose logs orchestrator | Select-String "9f5b5bfb"
```

Replace `9f5b5bfb` with any `request_id` visible in the logs to trace that specific incident end to end.

## Log Fields

| Field | Description |
|-------|-------------|
| timestamp | ISO 8601 UTC timestamp |
| level | INFO, WARNING, or ERROR |
| module | Python module name |
| request_id | Unique incident identifier propagated across all components |
| message | Structured event name such as CONSENSUS_REACHED or PATCH_PROMOTED |
