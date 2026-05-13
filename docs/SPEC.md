# Self-Healing Software Agent MVP Specification

## 1. Purpose

The Self-Healing Software Agent is an MVP incident-response system for a small FastAPI service named `sha-app`. It watches application logs and health metrics, correlates independent failure signals, diagnoses the likely failure class, applies an automated repair or recovery action when confidence is high enough, validates the service health, notifies operators, and stores successful failure fingerprints for faster future response.

The intended users are engineers, teaching assistants, and operators evaluating autonomous software remediation workflows. The system solves the demo problem of repeatedly detecting and resolving three incident families:

- A code bug in `app/payments.py`, especially a divide-by-zero in transaction processing.
- An infrastructure crash where the Docker container for `sha-app` is stopped or unreachable.
- Ambiguous low-confidence failures that must be escalated instead of automatically repaired.

The system must satisfy five user story acceptance criteria:

- US-01: code bug detection and autonomous repair.
- US-02: infrastructure crash recovery by container restart.
- US-03: FMG fast-path learning and GPT-4o skip on repeated known failures.
- US-04: low-confidence escalation with Slack notification logging and no automated fix.
- US-05: RAG-augmented diagnosis with retrieved runbook chunks visible in diagnosis logs.

All inter-module incident data must use the typed dataclasses in `brain/state.py`. Structured JSON logging is required for significant operations, using `logger.get_logger(...)` and including `extra={"request_id": rid}` where `rid` is the incident request ID when one exists.

## 2. Component Inventory

| Module name | File path | Responsibility |
|---|---|---|
| `orchestrator` | `orchestrator.py` | Redis subscriber and LangGraph workflow coordinator. Checks FMG, enriches incidents, diagnoses, routes, repairs/restarts, validates, updates FMG. |
| `brain.consensus` | `brain/consensus.py` | Aggregates drone signals in a sliding window and emits an `IncidentBundle` once consensus is reached. |
| `brain.diagnosis` | `brain/diagnosis.py` | Builds diagnosis prompts, calls GPT-4o when available, provides deterministic/fallback diagnosis, and returns a typed `BrainDecision`. |
| `brain.decision` | `brain/decision.py` | Routes a `BrainDecision` to escalation, code repair, or DevOps restart. |
| `brain.state` | `brain/state.py` | Defines `FailureClass`, `Signal`, `IncidentBundle`, and `BrainDecision` dataclasses. |
| `agents.code_repair` | `agents/code_repair.py` | Generates or reverts a code fix, writes it into the sandbox app, runs sandbox tests, promotes passing patches, and restarts `sha-app`. |
| `agents.devops` | `agents/devops.py` | Restarts the `sha-app` Docker container and confirms the app health endpoint returns HTTP 200. |
| `agents.validation` | `agents/validation.py` | Confirms health after repair/restart, stores successful signatures in FMG, and sends Slack notifications. |
| `fmg.fmg` | `fmg/fmg.py` | Stores failure signatures in SQLite and performs Dynamic Time Warping similarity matching for fast-path decisions. |
| `rag.embed` | `rag/embed.py` | Seeds a persistent Chroma collection from `rag/runbook.md` using SentenceTransformer embeddings or deterministic hash embeddings as fallback. |
| `rag.retrieve` | `rag/retrieve.py` | Retrieves relevant runbook chunks from Chroma and applies a keyword rerank for divide-by-zero queries. |
| `git_context.correlate` | `git_context/correlate.py` | Reads recent git commits from the repository root and extracts the most recent commit line touching `payments.py`. |
| `notify.slack` | `notify/slack.py` | Sends resolved/escalation Slack messages when configured, and always logs `SLACK_SENT` for traceability. |
| `monitoring.log_drone` | `monitoring/log_drone.py` | Reads new lines from `app/app.log` and publishes log error density signals. |
| `monitoring.metric_drone` | `monitoring/metric_drone.py` | Polls `/health` and publishes error-rate signals. |
| `monitoring.base_drone` | `monitoring/base_drone.py` | Base polling, baseline, z-score, reliability, Redis publish, and run loop for drones. |
| `app.main` | `app/main.py` | FastAPI application with `/health`, `/process`, and `/data`, plus error-rate middleware and app log writes. |
| `app.payments` | `app/payments.py` | Transaction processing logic used by `/process`. |
| `inject_failure` | `inject_failure.py` | CLI demo injector for `divide_by_zero`, `infra_crash`, and `ambiguous` failures. |
| `logger` | `logger.py` | JSON logging formatter and `get_logger(name)` factory. |

The Docker Compose runtime contains services `redis`, `sha-app`, `sha-sandbox`, `orchestrator`, `log-drone`, and `metric-drone`. The orchestrator container mounts the repository at `/workspace` and the Docker socket at `/var/run/docker.sock`.

## 3. Data Flow

### 3.1 Failure Injection

`inject_failure.py` is the demo entrypoint. It accepts either a positional failure type or `--type <failure_type>`.

Supported types:

- `divide_by_zero`
- `infra_crash`
- `ambiguous`

For `divide_by_zero`, `inject_divide_by_zero()` performs the following steps:

1. Clears `app/app.log`.
2. Checks `git config user.email`. If it is missing, sets fallback local author config:
   - `git config user.email demo@sha.local`
   - `git config user.name "SHA Demo"`
3. Generates a timestamp with `datetime.now().strftime("%H%M%S")`.
4. Writes buggy `app/payments.py` code containing `result = amount / 0` and an `# injection_id: <timestamp>` comment.
5. Runs `git add app/payments.py`.
6. Runs `git commit -m "refactor: optimize transaction calculation - <timestamp>"`.
7. Restarts the app container with `docker restart sha-app`.
8. Probes `http://localhost:8000/process` up to 5 times to trigger the runtime error.
9. Logs `FAILURE_INJECTED`.

For `infra_crash`, `inject_infra_crash()` clears `app/app.log`, stops `sha-app` with `docker stop sha-app`, logs `FAILURE_INJECTED`, and prints a demo message.

For `ambiguous`, `inject_ambiguous()` writes intermittent failure logic to `app/payments.py`, restarts `sha-app`, probes `/process`, logs `FAILURE_INJECTED`, and prints a demo message.

### 3.2 Application Signals

`app/main.py` exposes:

- `GET /health`: returns `{"status": "ok", "error_rate": <float>, "uptime": <float>}`.
- `GET|POST /process`: calls `process_transaction(amount, items)`.
- `GET /data`: returns `{"records": 42}`.

The HTTP middleware increments request and error counters. Exceptions from `/process` are written to `app.log` unless the exception contains `intermittent_failure`.

`monitoring.log_drone.LogDrone` tails `app/app.log` and returns `error_count / len(new_lines)` as signal type `log_error_density`.

`monitoring.metric_drone.MetricDrone` polls the health endpoint. It returns:

- `1.0` if the endpoint is unreachable or returns non-200.
- The JSON `error_rate` field if the endpoint returns HTTP 200.

### 3.3 Redis Signal Contract

All drones publish to Redis channel:

```text
tier1.alerts
```

The signal payload is JSON produced from `dataclasses.asdict(Signal)` with this schema:

```json
{
  "drone_id": "log_drone | metric_drone | <string>",
  "service": "sha-app",
  "signal_type": "log_error_density | error_rate | <string>",
  "value": 0.0,
  "reliability": 1.0,
  "timestamp": 1710000000.0,
  "request_id": "8-char-or-other-correlation-id"
}
```

`BaseDrone.publish(value, request_id)` constructs the `Signal`, publishes it to `tier1.alerts`, and logs `SIGNAL_PUBLISHED`.

### 3.4 Consensus

`orchestrator.main()` subscribes to `tier1.alerts`, logs every decoded `SIGNAL_PUBLISHED`, and passes raw JSON strings to `ConsensusEngine.ingest(raw)`.

`ConsensusEngine` defaults:

- `window_sec = 60`
- `threshold = 1.5`
- `min_signal_types = 2`

Signals are grouped by `service` in memory. On each ingest:

1. Parse raw JSON into `Signal`.
2. Append it to `self.window[signal.service]`.
3. Prune signals older than `time.time() - window_sec`.
4. Compute `distinct_types`.
5. Compute weighted vote as the sum of the highest reliability value per distinct signal type.
6. Log `CONSENSUS_TICK`.

Consensus is reached if any of these conditions is true:

- `distinct_types >= min_signal_types` and `weighted_vote >= threshold`.
- At least two `error_rate` signals have `value >= 1.0`.
- Any `error_rate` signal has `0.0 < value < 0.6` for ambiguous escalation demos.

On consensus, the engine logs `CONSENSUS_REACHED`, builds an `IncidentBundle`, clears the service window, and returns the bundle. The bundle `signal_trajectory` is the last 12 signal values sorted by timestamp.

### 3.5 LangGraph Workflow

`orchestrator.build_graph()` compiles a `StateGraph(dict)` with this node sequence and conditional routing:

```text
check_fmg
  -> route_plan          if FMG fast-path matched
  -> enrich              if FMG did not match
enrich
  -> diagnose
diagnose
  -> check_confidence
check_confidence
  -> escalate            if confidence < CONFIDENCE_THRESHOLD
  -> route_plan          otherwise
escalate
  -> END
route_plan
  -> repair              if route(decision) == "repair"
  -> devops              if route(decision) == "devops"
repair
  -> validate
devops
  -> validate
validate
  -> END
```

There is no explicit edge for `route(decision) == "escalate"` from `route_plan`; low-confidence decisions are expected to be caught by `check_confidence`.

### 3.6 FMG Fast Path

`node_check_fmg(state)` runs before RAG enrichment and GPT-4o diagnosis. It only considers FMG if the bundle contains a positive `log_error_density` signal. If there is no application log signal, it logs `FMG_SKIPPED` and continues to enrichment.

When eligible, it calls:

```python
get_fmg().fast_path(bundle.signal_trajectory, bundle.service, request_id=bundle.request_id)
```

The FMG threshold comes from:

```text
FMG_FAST_PATH_THRESHOLD
```

Default:

```text
0.87
```

If FMG returns a match, `node_check_fmg` builds a `BrainDecision` using the cached failure class and cached plan, sets `fmg_match="fast_path"`, sets `gpt4o_skipped=True`, logs `GPT4O_SKIPPED`, and routes directly to `route_plan`.

### 3.7 Enrichment

`node_enrich(state)` builds this query:

```text
error in <service>: <signal_type>=<value> <signal_type>=<value> ...
```

It retrieves two runbook chunks:

```python
retrieve(query, get_collection(), top_k=2, request_id=bundle.request_id)
```

It fetches recent git context:

```python
get_recent_commits(request_id=bundle.request_id)
```

The git repo path default is `"."`, which is the repository root in local execution and `/workspace` inside the orchestrator container. The resulting chunks and commits are written back into the existing `IncidentBundle` fields `retrieved_chunks` and `recent_commits`. The node logs `INCIDENT_ENRICHED`.

### 3.8 Diagnosis

`node_diagnose(state)` calls `diagnose(bundle)`.

The GPT-4o call location is `brain/diagnosis.py` inside `diagnose()`, in:

```python
client.chat.completions.create(
    model="gpt-4o",
    temperature=0,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ],
)
```

If `OPENAI_API_KEY` is missing or equals `sk-your-key-here`, diagnosis uses `_fallback_output(...)` and sets `gpt4o_skipped=True`.

If all signals are metric-only outages where every signal is `error_rate >= 1.0`, diagnosis takes a deterministic fallback path and returns `INFRA_CRASH` without calling GPT-4o.

For `CODE_BUG`, `_decision_from_output(...)` normalizes the `suspect_commit` by calling `extract_suspect_commit(bundle.recent_commits, request_id=bundle.request_id)`. The returned value is the full git commit summary line, not only the hash.

Diagnosis logs `DIAGNOSIS_COMPLETE` with:

- `request_id`
- `failure_class`
- `confidence`
- `suspect_commit`
- `retrieved_chunks`
- `fallback`
- `deterministic` when the metric-only outage path is used

### 3.9 Confidence and Routing

The confidence threshold comes from:

```text
CONFIDENCE_THRESHOLD
```

Default:

```text
0.60
```

`node_check_confidence(state)` marks `low_confidence=True` when `decision.confidence < threshold` and logs `CONFIDENCE_CHECKED`.

`node_escalate(state)` logs `ESCALATION_REQUIRED`, calls `send_notification(decision, bundle, resolved=False)`, and ends the graph.

`brain.decision.route(decision)` returns:

- `"escalate"` if `decision.confidence < CONFIDENCE_THRESHOLD`.
- `"repair"` if `decision.proposed_plan` is `PLAN_A` or `PLAN_B`.
- `"devops"` otherwise.

### 3.10 Code Repair Path

`node_repair(state)` calls `agents.code_repair.repair(state["decision"])`.

`repair(...)` behavior:

1. If `decision.suspect_commit` is set, log `COMMIT_REVERT_ATTEMPT` and call `_try_revert(decision.suspect_commit, rid)`.
2. `_try_revert(...)` runs `git revert --no-commit <commit_hash>`, then `python -m pytest tests/ -q`. If tests pass, commits `auto-revert: <commit_hash> caused incident <rid>`, logs `REVERT_PROMOTED`, and returns `True`. If tests fail, aborts the revert and returns `False`.
3. If revert does not apply or is not attempted, read `<app_path>/payments.py`.
4. Generate patched code with `_generate_patch(current_code, decision)`.
   - If no OpenAI client is configured, the offline patch replaces `amount / 0` with `amount / items`.
   - If an OpenAI client is configured, GPT-4o is asked to return the entire corrected Python file.
5. Copy app files into `sandbox_app`, write patched `sandbox_app/payments.py`, and copy `logger.py` into the sandbox if it exists.
6. Log `PATCH_GENERATED`.
7. Run sandbox tests in the Docker sandbox.

The sandbox test path is exactly:

```text
tests/unit/test_payments.py
```

The Docker command is:

```text
docker exec sha-sandbox python -m pytest tests/unit/test_payments.py -q --tb=short
```

If Docker CLI is unavailable, the Docker SDK fallback executes the same command inside `sha-sandbox`. If that also fails, it falls back to local `py_compile` of `sandbox_app/payments.py`.

On sandbox success, repair writes the patched code to `app/payments.py`, restarts `sha-app`, logs `PATCH_PROMOTED`, and returns `True`. On failure, it logs `SANDBOX_FAILED` and returns `False`.

### 3.11 DevOps Path

`node_devops(state)` calls `agents.devops.restart(state["decision"])`.

`restart(...)` restarts `sha-app` first with Docker CLI:

```text
docker restart sha-app
```

If Docker CLI is unavailable or restart fails, it falls back to Docker SDK. It then polls the health URL every 5 seconds for up to 12 attempts. The health URL is based on `APP_URL` when set; otherwise it uses the function default and ensures `/health` is appended. On HTTP 200, it logs `CONTAINER_RESTARTED` and returns `True`.

### 3.12 Validation, Notification, and FMG Storage Trigger

`node_validate(state)` calls:

```python
validate_and_close(state["decision"], state["bundle"], fmg=get_fmg())
```

`validate_and_close(...)` polls the app health URL every 5 seconds for up to 3 attempts. On HTTP 200:

1. Logs `HEALTH_CONFIRMED`.
2. If `fmg` is provided, calls `fmg.store(...)`.
3. Logs `FMG_UPDATED`.
4. Calls `send_notification(decision, bundle, resolved=True)`.
5. Returns `True`.

The FMG storage trigger is therefore a successful post-action health check in `agents/validation.py`. The stored values are:

- `trajectory=bundle.signal_trajectory`
- `failure_class=decision.failure_class.value`
- `confidence=decision.confidence`
- `service=bundle.service`
- `cached_plan=decision.proposed_plan`
- `request_id=rid`

If validation fails, it logs `VALIDATION_FAILED`, calls `send_notification(decision, bundle, resolved=False)`, and returns `False`.

`send_notification(...)` always logs `SLACK_SENT` when Slack is not configured, with `status_code=0`, `configured=False`, and the `resolved` flag. This is required for demo traceability.

## 4. Public Interfaces

This section documents the source-level Python signatures that cross module boundaries. Private helper functions are included when other modules or tests rely on their behavior or when they are essential to reproducing the implementation.

### 4.1 State Types

File: `brain/state.py`

```python
class FailureClass(str, Enum):
    CODE_BUG = "CODE_BUG"
    INFRA_CRASH = "INFRA_CRASH"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    CONFIG_DRIFT = "CONFIG_DRIFT"
    DEPENDENCY_CASCADE = "DEPENDENCY_CASCADE"
    ANOMALOUS_OUTPUT = "ANOMALOUS_OUTPUT"
```

```python
@dataclass
class Signal:
    drone_id: str
    service: str
    signal_type: str
    value: float
    reliability: float
    timestamp: float
    request_id: str
```

```python
@dataclass
class IncidentBundle:
    request_id: str
    service: str
    signals: List[Signal]
    signal_trajectory: List[float]
    recent_commits: str
    retrieved_chunks: List[str]
    weighted_vote: float
    timestamp: float
```

```python
@dataclass
class BrainDecision:
    request_id: str
    failure_class: FailureClass
    confidence: float
    affected_component: str
    proposed_plan: str
    reasoning: str
    suspect_commit: Optional[str]
    fmg_match: Optional[str]
    gpt4o_skipped: bool
    retrieved_chunks: List[str] = field(default_factory=list)
```

```python
def new_incident_timestamp() -> float
```

### 4.2 Orchestrator

File: `orchestrator.py`

```python
def get_fmg() -> FMG
def get_collection()
def get_consensus() -> ConsensusEngine
def node_check_fmg(state: dict) -> dict
def node_enrich(state: dict) -> dict
def node_diagnose(state: dict) -> dict
def node_check_confidence(state: dict) -> dict
def node_escalate(state: dict) -> dict
def node_repair(state: dict) -> dict
def node_devops(state: dict) -> dict
def node_validate(state: dict) -> dict
def route_after_fmg(state: dict) -> str
def route_after_confidence(state: dict) -> str
def route_plan(state: dict) -> str
def build_graph()
def main() -> None
```

Global singletons:

- `_fmg: FMG | None`
- `_collection`
- `_consensus: ConsensusEngine | None`

Environment defaults:

- `REDIS_URL=redis://localhost:6379`
- `CONSENSUS_WINDOW=60`
- `FMG_PATH=fmg.db`
- `FMG_FAST_PATH_THRESHOLD=0.87`
- `CONFIDENCE_THRESHOLD=0.60`

### 4.3 Consensus

File: `brain/consensus.py`

```python
class ConsensusEngine:
    def __init__(
        self,
        redis_url: str,
        window_sec: int = 60,
        threshold: float = 1.5,
        min_signal_types: int = 2,
    )

    def ingest(self, raw: str) -> IncidentBundle | None
```

Also implemented:

```python
def _prune(self) -> None
def _weighted_vote(self, signals: List[Signal]) -> float
```

The public `ingest` return type is `IncidentBundle | None`. The user-facing minimum signature requirement `Optional[IncidentBundle]` is equivalent.

### 4.4 Diagnosis

File: `brain/diagnosis.py`

```python
class DiagnosisOutput(BaseModel):
    failure_class: str
    confidence: float
    affected_component: str
    proposed_plan: str
    reasoning: str
    suspect_commit: Optional[str] = None
```

Actual source note: `DiagnosisOutput` has six fields. The implementation and prompt do not define a seventh field. `retrieved_chunks` is carried in `BrainDecision`, not in GPT JSON.

```python
def diagnose(bundle: IncidentBundle) -> BrainDecision
```

Supporting functions:

```python
def _get_client() -> OpenAI | None
def _fallback_output(bundle: IncidentBundle) -> DiagnosisOutput
def _is_metric_only_outage(bundle: IncidentBundle) -> bool
def _decision_from_output(
    bundle: IncidentBundle,
    parsed: DiagnosisOutput,
    skipped: bool,
) -> BrainDecision
def _build_user_message(bundle: IncidentBundle) -> str
```

Validators:

```python
def valid_class(cls, value: str) -> str
def valid_confidence(cls, value: float) -> float
def valid_plan(cls, value: str) -> str
```

### 4.5 Decision Routing

File: `brain/decision.py`

```python
def route(decision: BrainDecision) -> str
```

### 4.6 Code Repair Agent

File: `agents/code_repair.py`

```python
def repair(
    decision: BrainDecision,
    app_path: str = "app",
    sandbox_url: str = "http://localhost:9000",
) -> bool
```

Supporting functions:

```python
def _get_client() -> OpenAI | None
def _strip_code_fences(code: str) -> str
def _generate_patch(current_code: str, decision: BrainDecision) -> str
def _prepare_sandbox(
    app_path: Path,
    sandbox_app_path: Path,
    patched_code: str,
    rid: str,
) -> None
def _docker_exec(container_name: str, command: list[str], rid: str) -> tuple[bool, str]
def _restart_container(container_name: str, rid: str) -> bool
def _run_sandbox_tests(rid: str, sandbox_app_path: Path) -> tuple[bool, str]
def _try_revert(commit_hash: str, rid: str) -> bool
```

### 4.7 DevOps Agent

File: `agents/devops.py`

```python
def restart(
    decision: BrainDecision,
    container_name: str = "sha-app",
    health_url: str = "http://localhost:8000/health",
) -> bool
```

Supporting function:

```python
def _health_url(default_url: str) -> str
```

### 4.8 Validation Agent

File: `agents/validation.py`

```python
def validate_and_close(
    decision: BrainDecision,
    bundle: IncidentBundle,
    health_url: str = "http://localhost:8000/health",
    fmg: FMG | None = None,
) -> bool
```

Supporting function:

```python
def _health_url(default_url: str) -> str
```

### 4.9 FMG

File: `fmg/fmg.py`

```python
class FMG:
    def __init__(self, db_path: str = "fmg.db", fast_path_threshold: float = 0.87)

    def store(
        self,
        trajectory: list,
        failure_class: str,
        confidence: float,
        service: str,
        cached_plan: str,
        provenance: str = "SYSTEM_DERIVED",
        request_id: str = "none",
    ) -> str

    def fast_path(
        self,
        trajectory: list,
        service: str,
        request_id: str = "none",
    ) -> Optional[Tuple[str, str, float]]
```

Supporting functions:

```python
def _dtw_distance(seq_a: list, seq_b: list) -> float
def _init_db(self) -> None
def _create_tables(self) -> None
```

SQLite tables:

```sql
CREATE TABLE IF NOT EXISTS failure_signatures (
    id              TEXT PRIMARY KEY,
    trajectory      TEXT NOT NULL,
    failure_class   TEXT NOT NULL,
    confidence      REAL NOT NULL,
    service         TEXT NOT NULL,
    cached_plan     TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    created_at      REAL NOT NULL
);
```

```sql
CREATE TABLE IF NOT EXISTS fix_attempts (
    id              TEXT PRIMARY KEY,
    signature_id    TEXT NOT NULL,
    plan_type       TEXT NOT NULL,
    sandbox_result  TEXT NOT NULL,
    production_ok   INTEGER,
    created_at      REAL NOT NULL,
    FOREIGN KEY (signature_id) REFERENCES failure_signatures(id)
);
```

### 4.10 RAG

File: `rag/embed.py`

```python
class HashEmbeddingModel:
    def encode(self, texts)

def get_embedding_model()

def build_collection(
    runbook_path: str = "rag/runbook.md",
    persist_dir: str = ".chromadb",
) -> chromadb.Collection
```

The embedding model name is:

```text
all-MiniLM-L6-v2
```

`SentenceTransformer(..., local_files_only=True)` is attempted first. On failure, `HashEmbeddingModel` returns deterministic 384-length vectors generated from SHA-256 bytes.

File: `rag/retrieve.py`

```python
class HashEmbeddingModel:
    def encode(self, texts)

def get_model() -> Any

def retrieve(
    query: str,
    collection: chromadb.Collection,
    top_k: int = 2,
    request_id: str = "none",
) -> List[str]
```

For queries containing `"divide"` or `"zero"`, retrieval scans all documents and prepends chunks containing `CODE_BUG` or `ZeroDivisionError`, capped to `top_k`.

### 4.11 Git Context

File: `git_context/correlate.py`

```python
def get_recent_commits(
    repo_path: str = ".",
    hours: int = 6,
    request_id: str = "none",
) -> str
```

This runs:

```text
git log --since=<timestamp> --oneline --name-only --no-merges
```

with `cwd=repo_path`, where the default `"."` is required so the orchestrator container resolves `/workspace/.git`.

```python
def extract_suspect_commit(
    git_log: str,
    error_file: str = "payments.py",
    request_id: str = "none",
) -> Optional[str]
```

This returns the full commit summary line for the most recent commit that touched `payments.py`, such as:

```text
2f6465f refactor: optimize transaction calculation - 174841
```

### 4.12 Slack Notification

File: `notify/slack.py`

```python
def send_notification(
    decision: BrainDecision,
    bundle: IncidentBundle,
    resolved: bool = True,
) -> None
```

If `SLACK_WEBHOOK_URL` is absent or contains `your/webhook/url`, it logs `SLACK_NOT_CONFIGURED` and then logs `SLACK_SENT` with `status_code=0` and `configured=False`. If configured, it posts Slack blocks containing incident ID, service, failure class, confidence, suspect commit, and reasoning.

### 4.13 Monitoring Drones

File: `monitoring/base_drone.py`

```python
class BaseDrone:
    def __init__(
        self,
        drone_id: str,
        service: str,
        redis_url: str,
        poll_interval: int = 5,
        baseline_window: int = 120,
    )

    def read(self) -> float
    def signal_type(self) -> str
    def zscore(self, value: float) -> float
    def reliability(self) -> float
    def publish(self, value: float, request_id: str) -> None
    def run(self) -> None
```

File: `monitoring/log_drone.py`

```python
class LogDrone(BaseDrone):
    def __init__(self, log_file: str, **kwargs)
    def signal_type(self) -> str
    def read(self) -> float
```

Also implemented:

```python
def _initial_position(self) -> int
```

File: `monitoring/metric_drone.py`

```python
class MetricDrone(BaseDrone):
    def __init__(self, health_url: str, **kwargs)
    def signal_type(self) -> str
    def read(self) -> float
```

### 4.14 FastAPI App

File: `app/main.py`

```python
def write_app_log(level: str, message: str) -> None
def ensure_state() -> None
def startup() -> None
async def error_rate_middleware(request: Request, call_next)
def health()
def process(amount: float = 100.0, items: int = 5)
def data()
```

File: `app/payments.py`

```python
def process_transaction(amount: float, items: int) -> dict
```

Healthy implementation:

- Logs `PROCESS_TRANSACTION_STARTED`.
- If `items == 0`, logs `PROCESS_TRANSACTION_ERROR` and returns `{"result": None, "status": "error", "message": "Cannot divide by zero"}`.
- Otherwise returns `{"result": amount / items, "status": "ok"}`.

### 4.15 Failure Injection

File: `inject_failure.py`

```python
def _reset_app_log() -> None
def _run_container_command(command: list[str]) -> None
def _probe_process_endpoint() -> None
def inject_divide_by_zero()
def inject_infra_crash()
def inject_ambiguous()
```

CLI behavior:

```text
python inject_failure.py --type divide_by_zero
python inject_failure.py --type infra_crash
python inject_failure.py --type ambiguous
```

### 4.16 Logger

File: `logger.py`

```python
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str

def get_logger(name: str) -> logging.Logger
```

Log records include:

- `timestamp`
- `level`
- `module`
- `request_id`
- `message`
- all additional `extra` keys that are not standard logging record fields

## 5. Model and Prompt Selection

### 5.1 Diagnosis Model

The diagnosis model is:

```text
gpt-4o
```

The GPT-4o diagnosis call is in `brain/diagnosis.py` in `diagnose(bundle)`.

Parameters:

```python
model="gpt-4o"
temperature=0
response_format={"type": "json_object"}
```

### 5.2 Exact System Prompt

```text
You are a production incident diagnosis system.
You receive: (1) current signal values from monitoring drones,
(2) relevant runbook excerpts retrieved from an operational knowledge base,
(3) recent git commits that may have caused the failure.
You must return ONLY valid JSON matching the schema provided.
Base your diagnosis on the evidence given - do not guess.
```

### 5.3 Exact User Message Template

The exact template produced by `_build_user_message(bundle)` is:

```text

## Current Signals
Service: {bundle.service}
{signal_summary}

## Retrieved Runbook Context
{rag_context}

## Recent Git Commits (last 6 hours)
{git_context}

## Required Output Schema
{
  "failure_class":      one of CODE_BUG|INFRA_CRASH|SCHEMA_VIOLATION|CONFIG_DRIFT|DEPENDENCY_CASCADE|ANOMALOUS_OUTPUT,
  "confidence":         float between 0.0 and 1.0,
  "affected_component": string matching a known service name,
  "proposed_plan":      one of PLAN_A|PLAN_B|PLAN_C,
  "reasoning":          string explaining your diagnosis,
  "suspect_commit":     git hash string if a recent commit is likely the cause, else null
}
```

Where:

```python
signal_summary = "\n".join(
    f"- {signal.signal_type}: {signal.value:.3f} (reliability {signal.reliability:.2f})"
    for signal in bundle.signals
)
rag_context = "\n\n".join(bundle.retrieved_chunks) or "No runbook context retrieved."
git_context = bundle.recent_commits or "No recent commits."
```

The three required context sections are exactly:

- `## Current Signals`
- `## Retrieved Runbook Context`
- `## Recent Git Commits (last 6 hours)`

### 5.4 Expected JSON Output Schema

Actual source-of-truth schema from `DiagnosisOutput`:

```json
{
  "failure_class": "CODE_BUG | INFRA_CRASH | SCHEMA_VIOLATION | CONFIG_DRIFT | DEPENDENCY_CASCADE | ANOMALOUS_OUTPUT",
  "confidence": 0.0,
  "affected_component": "sha-app",
  "proposed_plan": "PLAN_A | PLAN_B | PLAN_C",
  "reasoning": "string",
  "suspect_commit": "string or null"
}
```

Validation constraints:

- `failure_class` must be one of the `FailureClass` enum values.
- `confidence` must be between `0.0` and `1.0`.
- `proposed_plan` must be one of `PLAN_A`, `PLAN_B`, or `PLAN_C`.

The assignment text may refer to seven `DiagnosisOutput` fields, but the actual implementation has six. Do not add `retrieved_chunks` to GPT output; it is stored in `BrainDecision.retrieved_chunks` after diagnosis.

### 5.5 Thresholds

Confidence threshold:

```text
CONFIDENCE_THRESHOLD=0.60
```

Implementation:

```python
float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
```

FMG fast-path threshold:

```text
FMG_FAST_PATH_THRESHOLD=0.87
```

Implementation:

```python
float(os.getenv("FMG_FAST_PATH_THRESHOLD", "0.87"))
```

### 5.6 Fallback Diagnosis Rules

If GPT-4o is unavailable, `_fallback_output(bundle)` returns deterministic outputs:

- If `0.0 < max_signal_value < 0.6`: `ANOMALOUS_OUTPUT`, confidence `0.45`, plan `PLAN_C`.
- If `error_rate >= 1.0` and `log_error_density == 0.0`: `INFRA_CRASH`, confidence `0.88`, plan `PLAN_C`.
- If retrieved runbook text contains `CODE_BUG` or `log_error_density > 0.0`: `CODE_BUG`, confidence `0.91`, plan `PLAN_A`.
- Otherwise: `ANOMALOUS_OUTPUT`, confidence `0.45`, plan `PLAN_C`.

The metric-only outage shortcut in `diagnose(bundle)` takes precedence over GPT-4o and returns the fallback `INFRA_CRASH` decision with `deterministic=True` in the log.

### 5.7 Required Runbook Sections

`rag/runbook.md` must contain at least these headings and operational meanings:

- `## CODE_BUG`: runtime application logic defects such as `ZeroDivisionError`; repair by patching and validating in sandbox; maps divide-by-zero in `app/payments.py` to `PLAN_A`.
- `## INFRA_CRASH`: unreachable or stopped service without matching Python business exception; restart Docker container; maps stopped `sha-app` to `PLAN_C`.
- `## AMBIGUOUS`: mixed or inconsistent signals below the confidence threshold; escalate to a human.
- `## SCHEMA_VIOLATION`: database schema change breaks dependent services; escalate unless a direct rollback is safe.
- `## CONFIG_DRIFT`: configuration change degrades fleet behavior; trigger config rollback via DevOps agent.

Seeding splits the runbook on blank-line-separated chunks longer than 50 characters, so each section body must be separated by blank lines.

