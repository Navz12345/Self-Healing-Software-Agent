# Models

## Diagnosis

- Model ID: `gpt-4o`
- Provider: OpenAI
- Use: grounded incident diagnosis and code patch generation when `OPENAI_API_KEY` is configured.

## Embeddings

- Model ID: `all-MiniLM-L6-v2`
- Library: sentence-transformers
- Use: local embeddings for ChromaDB runbook retrieval.

The implementation includes deterministic fallbacks for local testing when API keys or model network access are unavailable.
