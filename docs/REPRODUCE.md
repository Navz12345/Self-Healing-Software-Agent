# Reproduce

Expected environment:

- Python 3.11
- Docker Compose
- 4 CPU cores and 8 GB RAM recommended

Commands:

```bash
cp .env.example .env
docker compose up
make test
make lint
python inject_failure.py --type divide_by_zero
python inject_failure.py --type infra_crash
python inject_failure.py --type divide_by_zero
```

Expected demo recovery targets:

- Code bug: under 60 seconds
- Infrastructure crash: under 60 seconds
- FMG repeat path: under 20 seconds for diagnosis skip logs
