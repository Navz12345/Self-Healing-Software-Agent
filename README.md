# Self-Healing Software Agent

An MVP autonomous incident-response system for a FastAPI target application. Scout drones publish signals to Redis, the consensus brain creates incidents, diagnosis uses GPT-4o plus RAG and git context, specialist agents repair or restart, and FMG learns repeated failures.

## Tech Stack

- FastAPI 0.111.0 + Uvicorn 0.29.0
- LangGraph 0.0.55 for orchestration graph
- OpenAI GPT-4o for diagnosis and patch generation
- ChromaDB 0.5.0 + sentence-transformers for RAG
- Redis 5.0.4 for signal passing
- SQLite via aiosqlite for FMG fingerprint storage
- Docker Compose for deployment

## Quickstart

```bash
cp .env.example .env
docker compose up
```

In a second terminal:

```bash
python inject_failure.py --type divide_by_zero
python inject_failure.py --type infra_crash
python inject_failure.py --type divide_by_zero
```

Watch `docker compose logs` for `CONSENSUS_REACHED`, `PATCH_PROMOTED`, `CONTAINER_RESTARTED`, `FMG_FAST_PATH_FIRED`, and `GPT4O_SKIPPED`.

## Checks

```bash
make test
make lint
make loadtest
make demo
```

## Results

| Metric | Value | Tolerance |
|--------|-------|-----------|
| Load test throughput | 31.86 req/s | +/- 5 req/s |
| Load test error rate | 0% | < 5% |
| Test coverage | 74.34% | +/- 2% |
| User story pass rate | 5/5 | -- |
| Avg response time | 3.43ms | +/- 1ms |
| FMG fast-path resolution | < 12 seconds | +/- 3s |
| Demo cost (all 5 stories) | < $0.50 | -- |

## Observability (Work in Progress)
Prometheus and Grafana configuration files are included in `monitoring/` as a work-in-progress addition. The infrastructure starts with `docker compose up -d prometheus grafana` but full metric scraping and dashboard panels are not yet wired to the application. This is planned for the next iteration after the MVP.
