# Model Card

## Intended Use

This system is intended for autonomous detection, diagnosis, and repair of software failures in containerized FastAPI microservices. It is designed for development and staging environments where teams want to reduce mean time to recovery for known failure classes. Primary users are software engineering teams running Docker-based deployments.

## Limitations

- The system is trained on a single application (payments.py) and may not generalize patch generation to other codebases without adaptation
- GPT-4o diagnosis accuracy depends on the quality of the RAG runbook
- The FMG fast-path requires prior exposure to a failure pattern; novel failures always go through GPT-4o
- The sentence-transformers model runs without GPU; embedding quality degrades gracefully via hash fallback when model weights are unavailable
- Confidence thresholds are fixed at 0.60 and 0.87; these may require tuning for different applications

## Risks

- Automated patch promotion without human review can introduce regressions if sandbox tests do not cover edge cases
- False positive INFRA_CRASH classification can trigger unnecessary container restarts
- Git commit correlation may flag innocent commits near a failure window
- The system requires OPENAI_API_KEY which has cost implications at scale
- Slack webhook URL should be treated as a secret and not committed to VCS

## Out of Scope

- Production systems handling real financial transactions or PII
- Multi-service or distributed tracing across more than one application
- Failure classes beyond CODE_BUG and INFRA_CRASH in the automated repair path (SCHEMA_VIOLATION and CONFIG_DRIFT are diagnosed but not automatically repaired in this MVP)
- Windows or macOS native deployment (Docker is required)
- Real-time streaming dashboards or Grafana integration
