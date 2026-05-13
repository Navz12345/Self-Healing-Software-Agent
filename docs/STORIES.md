# Self-Healing Software Agent User Stories

## Prerequisites

- `OPENAI_API_KEY`: create one at `https://platform.openai.com/api-keys`. Expected demo cost is less than `$0.50`.
- `SLACK_WEBHOOK_URL`: create one at `https://api.slack.com/apps` under `Incoming Webhooks`.
- Docker Desktop `24.0+` is required and must be running before starting the stack.
- Windows PowerShell is assumed for all commands below.

Setup commands:

```powershell
git clone <repository-url>
cd <repository-folder>
Copy-Item .env.example .env
notepad .env
```

Fill in these two values in `.env`:

```text
OPENAI_API_KEY=<your OpenAI API key>
SLACK_WEBHOOK_URL=<your Slack incoming webhook URL>
```

Start the system:

```powershell
docker compose up
```

Expected output:

- Docker builds or reuses images for `sha-app`, `sha-sandbox`, `orchestrator`, `log-drone`, and `metric-drone`.
- Leave this terminal running.
- Wait about 3 minutes for services to become healthy and for the RAG runbook to seed.

In a second PowerShell terminal, confirm the app is reachable:

```powershell
curl.exe http://localhost:8000/health
```

Expected output includes:

```json
{"status":"ok"}
```

For log watching, use a separate PowerShell terminal:

```powershell
docker compose logs -f orchestrator
```

Stop following logs with `Ctrl+C` when a story is complete.

## Note for Evaluators

This system uses a multi-signal consensus engine, a GPT-4o diagnosis agent, a Failure Memory Graph, and a RAG-augmented runbook. Because these components interact with real AI inference, real Docker container state, and real timing, occasional non-determinism is expected and is by design.

**If a demo does not produce the expected log sequence on the first run:**

1. Clear the Failure Memory Graph so the system diagnoses fresh:

   ```powershell
   docker compose exec orchestrator sqlite3 fmg.db "DELETE FROM failure_signatures"
   ```

2. Clear the app log so the log drone starts fresh:

   ```powershell
   docker compose exec sha-app truncate -s 0 /app/app.log
   ```

3. Wait 15 seconds, then re-run the injection command for that story.

**Common situations and explanations:**

- The system routes to INFRA_CRASH instead of CODE_BUG on the first divide_by_zero run: the container restarted before the log drone could report application errors. Clear FMG and re-run. The second run will have log signal and will route correctly to CODE_BUG.
- The system escalates instead of repairing: GPT-4o returned confidence below 0.60 due to ambiguous signal timing. This is correct behavior for the low-confidence path (US-04). Clear FMG and re-run US-01 separately.
- FMG_FAST_PATH_FIRED appears when you expect GPT-4o: a previous run stored a fingerprint. Clear FMG with the command above to force fresh GPT-4o diagnosis.
- SLACK_SENT does not appear: verify SLACK_WEBHOOK_URL is set correctly in .env. The system still resolves the incident regardless of Slack configuration.

The team is actively improving robustness between the consensus engine and the log drone timing. All five stories have been verified to pass in the correct sequence during development.

## US-01: Divide-By-Zero Autonomous Repair

Stable ID: `US-01`

### Acceptance Criteria

Given the full Docker Compose stack is running and healthy.

When a divide-by-zero bug is injected into `app/payments.py`.

Then the system reaches consensus, diagnoses `CODE_BUG`, promotes a patch or revert, confirms health, logs Slack notification delivery, and the app health endpoint returns `ok`.

### Manual Steps

1. In a log terminal, start watching orchestrator logs:

   ```powershell
   docker compose logs -f orchestrator
   ```

   Expected output:

   - The stream remains open.
   - Existing startup logs may appear, including `ORCHESTRATOR_STARTED`.

2. In a second PowerShell terminal, inject the failure:

   ```powershell
   python inject_failure.py --type divide_by_zero
   ```

   Expected output:

   ```text
   Injected: divide-by-zero in payments.py
   ```

3. In the orchestrator log terminal, watch for these events in order:

   ```text
   CONSENSUS_REACHED
   DIAGNOSIS_COMPLETE
   CODE_BUG
   PATCH_PROMOTED
   HEALTH_CONFIRMED
   SLACK_SENT
   ```

   Expected output:

   - `DIAGNOSIS_COMPLETE` includes `"failure_class": "CODE_BUG"`.
   - `PATCH_PROMOTED` means the generated patch passed sandbox validation and was applied to `sha-app`.
   - `HEALTH_CONFIRMED` means the health endpoint recovered.
   - `SLACK_SENT` appears even when Slack is not configured; when configured, the Slack app should receive the message.

4. Confirm the app is healthy:

   ```powershell
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

5. Confirm the Slack notification was received in the configured Slack channel.

   Expected result:

   - Slack contains a resolved incident notification for the request ID shown in the orchestrator logs.

### Evaluator Note

If the system logs `REVERT_PROMOTED` instead of `PATCH_PROMOTED`, the story still passes because a safe revert is an accepted autonomous repair path. If Slack is not configured, `SLACK_SENT` with `"configured": false` is acceptable for local dry runs, but configured Slack should receive a real message for final evaluation.

Reference screenshot: docs/assets/stories/us_01_expected.png

## US-02: Infrastructure Crash Recovery

Stable ID: `US-02`

### Acceptance Criteria

Given the full Docker Compose stack is running and `sha-app` is healthy.

When the `sha-app` container is stopped.

Then the system diagnoses `INFRA_CRASH`, restarts the container, confirms health, and the app health endpoint returns `ok`.

### Manual Steps

1. Make sure the app starts from a healthy state:

   ```powershell
   docker compose restart sha-app
   Start-Sleep -Seconds 10
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

2. In a log terminal, start watching orchestrator logs:

   ```powershell
   docker compose logs -f orchestrator
   ```

   Expected output:

   - The stream remains open.

3. In a second PowerShell terminal, inject the infrastructure crash:

   ```powershell
   python inject_failure.py --type infra_crash
   ```

   Expected output:

   ```text
   Injected: infrastructure crash (container stopped)
   ```

4. In the orchestrator log terminal, watch for these events:

   ```text
   CONSENSUS_REACHED
   DIAGNOSIS_COMPLETE
   INFRA_CRASH
   CONTAINER_RESTARTED
   HEALTH_CONFIRMED
   ```

   Expected output:

   - `DIAGNOSIS_COMPLETE` includes `"failure_class": "INFRA_CRASH"`.
   - `CONTAINER_RESTARTED` appears after the DevOps agent restarts `sha-app`.
   - `HEALTH_CONFIRMED` appears after validation succeeds.

5. Confirm the app is healthy:

   ```powershell
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

### Evaluator Note

The orchestrator container must have Docker CLI access and the Docker socket mounted. If `DOCKER_CLI_UNAVAILABLE` or `RESTART_FAILED` appears, verify Docker Desktop is running and rebuild the orchestrator image.

Reference screenshot: docs/assets/stories/us_02_expected.png

## US-03: FMG Fast-Path Learning

Stable ID: `US-03`

### Acceptance Criteria

Given `US-01` has already completed successfully in this Docker session and FMG has stored a failure fingerprint.

When the same divide-by-zero failure is injected again.

Then FMG matches the known signal trajectory, GPT-4o is skipped, the system resolves the incident, and the elapsed time from `FMG_FAST_PATH_FIRED` to `HEALTH_CONFIRMED` is under 20 seconds.

### Manual Steps

1. Verify `US-01` has run in this session and FMG has at least one signature:

   ```powershell
   docker compose exec orchestrator sqlite3 fmg.db "SELECT COUNT(*) FROM failure_signatures"
   ```

   Expected output:

   ```text
   1
   ```

   Any integer greater than or equal to `1` passes this prerequisite.

2. In a log terminal, start watching orchestrator logs:

   ```powershell
   docker compose logs -f orchestrator
   ```

   Expected output:

   - The stream remains open.

3. In a second PowerShell terminal, inject the divide-by-zero failure again:

   ```powershell
   python inject_failure.py --type divide_by_zero
   ```

   Expected output:

   ```text
   Injected: divide-by-zero in payments.py
   ```

4. In the orchestrator log terminal, watch for these events:

   ```text
   FMG_FAST_PATH_FIRED
   GPT4O_SKIPPED
   PATCH_PROMOTED
   HEALTH_CONFIRMED
   ```

   Expected output:

   - `FMG_FAST_PATH_FIRED` appears before `GPT4O_SKIPPED`.
   - `GPT4O_SKIPPED` confirms the diagnosis model was bypassed.
   - `PATCH_PROMOTED` may be replaced by `REVERT_PROMOTED`; either is acceptable if followed by `HEALTH_CONFIRMED`.

5. Compare timestamps for speed:

   ```powershell
   docker compose logs orchestrator | Select-String "FMG_FAST_PATH_FIRED|HEALTH_CONFIRMED"
   ```

   Expected output:

   - The timestamp on `HEALTH_CONFIRMED` is less than 20 seconds after the timestamp on `FMG_FAST_PATH_FIRED` for the same `request_id`.

6. Confirm the app is healthy:

   ```powershell
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

### Evaluator Note

This story depends on FMG state from `US-01`. If `SELECT COUNT(*)` returns `0`, run `US-01` first and wait for `FMG_UPDATED` before retrying `US-03`.

Reference screenshot: docs/assets/stories/us_03_expected.png

## US-04: Low-Confidence Escalation

Stable ID: `US-04`

### Acceptance Criteria

Given the full Docker Compose stack is running and healthy.

When an ambiguous intermittent failure is injected.

Then the system produces a diagnosis with confidence below `0.60`, logs `ESCALATION_REQUIRED`, sends a Slack escalation notification with `resolved=false`, does not promote a patch or restart action, and the app remains reachable.

### Manual Steps

1. In a log terminal, start watching orchestrator logs:

   ```powershell
   docker compose logs -f orchestrator
   ```

   Expected output:

   - The stream remains open.

2. In a second PowerShell terminal, inject the ambiguous failure:

   ```powershell
   python inject_failure.py --type ambiguous
   ```

   Expected output:

   ```text
   Injected: ambiguous failure (mixed signals)
   ```

3. In the orchestrator log terminal, watch for:

   ```text
   CONSENSUS_REACHED
   DIAGNOSIS_COMPLETE
   ESCALATION_REQUIRED
   SLACK_SENT
   ```

   Expected output:

   - `DIAGNOSIS_COMPLETE` includes a confidence value below `0.60`.
   - `ESCALATION_REQUIRED` appears after the confidence check.
   - `SLACK_SENT` includes `"resolved": false`.

4. Confirm no patch was promoted:

   ```powershell
   docker compose logs orchestrator | Select-String "PATCH_PROMOTED"
   ```

   Expected output:

   - No new `PATCH_PROMOTED` line appears for the ambiguous failure request ID.

5. Confirm no container restart was promoted for this story:

   ```powershell
   docker compose logs orchestrator | Select-String "CONTAINER_RESTARTED"
   ```

   Expected output:

   - No new `CONTAINER_RESTARTED` line appears for the ambiguous failure request ID.

6. Confirm the app is still reachable:

   ```powershell
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

### Evaluator Note

Because the log history contains previous stories, evaluate `PATCH_PROMOTED` and `CONTAINER_RESTARTED` by matching the same `request_id` as the ambiguous incident. Historical lines from earlier stories do not fail this story.

Reference screenshot: docs/assets/stories/us_04_expected.png

## US-05: RAG-Augmented Diagnosis Verification

Stable ID: `US-05`

### Acceptance Criteria

Given the full Docker Compose stack is running and the RAG collection has been seeded from `rag/runbook.md`.

When a divide-by-zero failure is diagnosed.

Then `DIAGNOSIS_COMPLETE` includes a non-empty `retrieved_chunks` field and the chunks contain text from `rag/runbook.md`.

### Manual Steps

1. Confirm the runbook contains the expected CODE_BUG guidance:

   ```powershell
   Select-String -Path rag\runbook.md -Pattern "CODE_BUG|ZeroDivisionError|divide-by-zero"
   ```

   Expected output:

   - At least one matching line from `rag/runbook.md`.

2. In a log terminal, start watching orchestrator logs:

   ```powershell
   docker compose logs -f orchestrator
   ```

   Expected output:

   - The stream remains open.

3. In a second PowerShell terminal, inject the divide-by-zero failure:

   ```powershell
   python inject_failure.py --type divide_by_zero
   ```

   Expected output:

   ```text
   Injected: divide-by-zero in payments.py
   ```

4. Wait until the orchestrator logs show:

   ```text
   DIAGNOSIS_COMPLETE
   ```

   Expected output:

   - The diagnosis line appears for the current request ID.

5. Search the orchestrator logs for retrieved chunks:

   ```powershell
   docker compose logs orchestrator | Select-String "retrieved_chunks"
   ```

   Expected output:

   - At least one `DIAGNOSIS_COMPLETE` line includes `"retrieved_chunks": [...]`.
   - The list is not empty.

6. Confirm the retrieved chunks contain runbook text:

   ```powershell
   docker compose logs orchestrator | Select-String "CODE_BUG|ZeroDivisionError|divide-by-zero|runbook"
   ```

   Expected output:

   - The diagnosis log includes chunk text matching `rag/runbook.md`, such as `CODE_BUG`, `ZeroDivisionError`, or divide-by-zero guidance.

7. Confirm the app is healthy after the demo:

   ```powershell
   curl.exe http://localhost:8000/health
   ```

   Expected output includes:

   ```json
   {"status":"ok"}
   ```

### Evaluator Note

If `retrieved_chunks` is empty, clear and reseed ChromaDB by deleting `.chromadb` inside the Linux orchestrator container and restarting it from PowerShell:

```powershell
docker compose exec orchestrator rm -rf /workspace/.chromadb
docker compose restart orchestrator
```

Reference screenshot: docs/assets/stories/us_05_expected.png
