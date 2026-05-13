# Logging

All modules use `get_logger` from `logger.py`. Logs are JSON objects with `timestamp`, `level`, `module`, `request_id`, and `message`.

Example trace:

```json
{"message":"SIGNAL_PUBLISHED","request_id":"abc12345"}
{"message":"CONSENSUS_REACHED","request_id":"abc12345"}
{"message":"RAG_RETRIEVED","request_id":"abc12345"}
{"message":"DIAGNOSIS_COMPLETE","request_id":"abc12345"}
{"message":"PATCH_PROMOTED","request_id":"abc12345"}
{"message":"HEALTH_CONFIRMED","request_id":"abc12345"}
```
