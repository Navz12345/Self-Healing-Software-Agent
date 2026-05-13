# Model Card

## GPT-4o

Provider: OpenAI.

Client library: `openai==1.30.0`.

Runtime settings:

- `temperature=0`
- `max_tokens=800`

Uses:

- Incident diagnosis in `brain/diagnosis.py`.
- Patch generation in `agents/code_repair.py`.

Input format:

```json
{
  "signal_summary": [
    {"signal_type": "error_rate", "value": 1.0},
    {"signal_type": "log_error_density", "value": 0.8}
  ],
  "rag_context": [
    "Runbook chunks retrieved from ChromaDB"
  ],
  "git_context": [
    "Recent commits touching payments.py"
  ]
}
```

The diagnosis prompt is organized into three context sections:

- `signal_summary`: signal type and value pairs from the consensus bundle.
- `rag_context`: runbook chunks retrieved from ChromaDB.
- `git_context`: recent git commits, especially commits touching `payments.py`.

Output format:

```json
{
  "failure_class": "CODE_BUG",
  "confidence": 0.91,
  "suspect_commit": "2f6465f refactor: optimize transaction calculation - 174841",
  "patch": "corrected Python source or null",
  "reasoning": "Application logs and runbook context indicate a divide-by-zero code bug."
}
```

Field requirements:

- `failure_class`: one of `CODE_BUG`, `INFRA_CRASH`, `SCHEMA_VIOLATION`, `CONFIG_DRIFT`, `DEPENDENCY_CASCADE`, or `ANOMALOUS_OUTPUT`.
- `confidence`: float from `0.0` to `1.0`.
- `suspect_commit`: full commit summary line when available, otherwise `null`.
- `patch`: corrected source code when the model is used for patch generation, otherwise `null`.
- `reasoning`: short explanation grounded in the supplied signals, RAG chunks, and git context.

Fallback:

- A deterministic `INFRA_CRASH` guard bypasses GPT-4o for metric-only bundles.
- If all incident signals are `error_rate >= 1.0` and no application log error signal is present, the system classifies the incident as `INFRA_CRASH` without calling GPT-4o.
- If `OPENAI_API_KEY` is missing, the system uses deterministic fallback diagnosis and an offline divide-by-zero patch strategy.

## all-MiniLM-L6-v2

Provider: `sentence-transformers`.

Embedding dimension: `384`.

Runtime mode:

- Used offline via cached weights.
- No network call is required at inference time when the weights are already cached.
- If cached weights are unavailable, the MVP falls back to deterministic hash embeddings so local demos can still run.

Uses:

- Embed runbook chunks from `rag/runbook.md` at startup.
- Embed incident query vectors at incident time.
- Retrieve matching chunks from ChromaDB.

Storage:

- Embeddings are stored in ChromaDB at `.chromadb/`.

## Training and Fine-Tuning

No model training or fine-tuning is performed.

The system uses hosted GPT-4o inference and local/cached sentence-transformer embeddings only.

## Cost

Total inference cost for all five demos is expected to be under `$0.50`.

FMG fast-path learning reduces repeated GPT-4o calls by skipping diagnosis for known signal trajectories.
