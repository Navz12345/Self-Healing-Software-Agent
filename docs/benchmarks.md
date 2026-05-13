# Benchmarks

## Hardware Profile

Tests were run on Windows 11 with Docker Desktop.
Host: Intel/AMD x86-64, 8 GB RAM, 4 CPU cores allocated to Docker.

## Methodology

Load test: Locust with 10 concurrent users targeting GET /health over a 60-second window. The endpoint returns JSON with status, error_rate, and uptime fields.

Command:

```bash
make loadtest
```

## Headline Numbers

| Metric | Value |
|--------|-------|
| Requests per second | 31.86 |
| Total requests | 1899 |
| Failure count | 0 |
| Failure rate | 0% |
| Average response time | 3.43ms |
| Median response time | 2ms |
| 95th percentile | 8ms |
| Peak throughput | ~35 req/s |

## Test Coverage

| Category | Files | Pass Rate |
|----------|-------|-----------|
| Unit | tests/unit/ | 21/21 |
| Integration | tests/integration/ | 1/1 |
| User stories | tests/user_stories/ | 5/5 |
| Edge cases | tests/edge/ | 2/2 |
| Total | all | 28/28 |

Coverage: 74.34% on business logic modules.

## Autonomous Recovery Benchmarks

| Scenario | Detection Time | Recovery Time | Total MTTR |
|----------|---------------|---------------|------------|
| CODE_BUG divide-by-zero | < 15 seconds | < 45 seconds | < 60 seconds |
| INFRA_CRASH container stop | < 15 seconds | < 30 seconds | < 45 seconds |
| FMG fast-path repeat | < 5 seconds | < 12 seconds | < 20 seconds |
| Low confidence escalation | < 15 seconds | N/A (escalated) | < 20 seconds |
