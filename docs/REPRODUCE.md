# Reproduce

## Hardware Profile

- CPU: 4 cores minimum, 8 cores recommended
- RAM: 8 GB minimum, 16 GB recommended
- Disk: 10 GB free for Docker images and model weights
- OS: Windows 10/11 with Docker Desktop, macOS, or Linux
- Network: Required for initial Docker image pull and OpenAI API calls

## Expected Runtime

- docker compose up --build: 8-10 minutes on first run
- make test: 35-45 seconds
- make lint: 10-15 seconds
- All five demos end to end: approximately 5 minutes

## One Command Replay

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY and SLACK_WEBHOOK_URL in .env
make reproduce
```

## Expected Metric Values

| Metric | Expected | Tolerance |
|--------|----------|-----------|
| Test pass rate | 28/28 | 0 failures |
| Test coverage | 74.48% | +/- 2% |
| Load test throughput | 31.86 req/s | +/- 5 req/s |
| Load test error rate | 0% | < 5% |
| Code bug repair time | < 60 seconds | +/- 10s |
| Infra crash recovery time | < 60 seconds | +/- 10s |
| FMG fast-path resolution | < 20 seconds | +/- 5s |

## Seed and Determinism

Random seed: 42 (set in grading/manifest.yaml)
GPT-4o temperature: 0 (deterministic inference)
ChromaDB: seeded from rag/runbook.md on first startup

## Known Variance Sources

- GPT-4o response time varies with OpenAI API load (+/- 3 seconds)
- FMG similarity scores are deterministic given same signal trajectory
- Load test throughput varies with host CPU (+/- 5 req/s)

## Important: Service Health
After running `docker compose up -d`, wait for all services to report healthy before running tests. The `make reproduce` target waits 180 seconds automatically. To check manually run: `docker compose ps` and verify all services show `healthy` status.

