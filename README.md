# Self-Healing Software Agent

An MVP autonomous incident-response system for a FastAPI target application. Scout drones publish signals to Redis, the consensus brain creates incidents, diagnosis uses GPT-4o plus RAG and git context, specialist agents repair or restart, and FMG learns repeated failures.

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
| Load test throughput | 31.86 req/s | ± 5 req/s |
| Load test error rate | 0% | < 5% |
| Test coverage | 74.34% | ± 2% |
| User story pass rate | 5/5 | — |
| Avg response time | 3.43ms | ± 1ms |
| FMG fast-path resolution | < 12 seconds | ± 3s |
| Demo cost (all 5 stories) | < $0.50 | — |
