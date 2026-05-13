# UTSA Runbook

## Primary setup

- Student: `microsoft/Phi-3.5-mini-instruct`
- Teacher: `llama-3.3-70b-instruct-awq`
- Judge: `llama-3.3-70b-instruct-awq`
- Primary config: `configs/full_phi35_utsa.yaml`
- Fallback config: `configs/fallback_qwen3_utsa.yaml`

## Environment variables

Keep secrets in your shell session or a local `.env` file that is not committed:

- `HF_TOKEN`
- `UTSA_QWEN_API_KEY`
- `UTSA_QWEN_BASE_URL`
- `UTSA_LLAMA_API_KEY`
- `UTSA_LLAMA_BASE_URL`

## Suggested execution order

1. Activate your Python environment
2. Export the required environment variables
3. Connect to UTSA VPN for Llama teacher and judge access
4. Build the full JSON prompt seed file
5. Prepare datasets
6. Generate teacher JSON outputs
7. Prepare Stage 1 and Stage 2 training plans
8. Submit UTSA HPC jobs
9. Run inference at checkpoints 0, 1, and 2
10. Run metrics, judge comparisons, and aggregation
11. Fill the report template with measured values and qualitative examples

## Why this setup is defensible in the report

- Phi-3.5 Mini Instruct is explicitly recommended in the assignment
- Llama 3.3 70B is a strong teacher/judge for imitation learning and pairwise evaluation
- The fallback path is documented but separate, so your main results stay coherent
- Prompt seeds cover all five required JSON task families
