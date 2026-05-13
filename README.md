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
