import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from logger import get_logger

try:
    from database import initialize
    from payments import process_transaction
except ImportError:
    from app.database import initialize
    from app.payments import process_transaction


app = FastAPI()
log = get_logger(__name__)
APP_LOG = Path("app.log")


def write_app_log(level: str, message: str) -> None:
    with APP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{level} {message}\n")


def ensure_state() -> None:
    if not hasattr(app.state, "start_time"):
        app.state.start_time = time.time()
    if not hasattr(app.state, "request_count"):
        app.state.request_count = 0
    if not hasattr(app.state, "error_count"):
        app.state.error_count = 0
    if not hasattr(app.state, "error_rate"):
        app.state.error_rate = 0.0


@app.on_event("startup")
def startup() -> None:
    ensure_state()
    initialize()
    log.info("APP_STARTED", extra={"request_id": "none"})


@app.middleware("http")
async def error_rate_middleware(request: Request, call_next):
    ensure_state()
    rid = request.headers.get("x-request-id", "none")
    app.state.request_count += 1
    log.info(
        "HTTP_REQUEST_STARTED",
        extra={"request_id": rid, "method": request.method, "path": request.url.path},
    )
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            app.state.error_count += 1
        return response
    except Exception as exc:
        app.state.error_count += 1
        log.error(
            "HTTP_REQUEST_FAILED",
            extra={"request_id": rid, "path": request.url.path, "error": str(exc)},
        )
        if "intermittent_failure" not in str(exc):
            write_app_log("ERROR", f"HTTP_REQUEST_FAILED path={request.url.path} error={exc}")
        raise
    finally:
        app.state.error_rate = app.state.error_count / max(app.state.request_count, 1)


@app.get("/health")
def health():
    ensure_state()
    return {
        "status": "ok",
        "error_rate": app.state.error_rate,
        "uptime": time.time() - app.state.start_time,
    }


@app.post("/process")
@app.get("/process")
def process(amount: float = 100.0, items: int = 5):
    try:
        result = process_transaction(amount, items)
        log.info("PROCESS_ENDPOINT_OK", extra={"request_id": "none"})
        return result
    except Exception as exc:
        log.error("PROCESS_ENDPOINT_ERROR", extra={"request_id": "none", "error": str(exc)})
        if "intermittent_failure" not in str(exc):
            write_app_log("ERROR", f"ERROR in process_transaction: {exc}")
        raise


@app.get("/data")
def data():
    log.info("DATA_ENDPOINT_READ", extra={"request_id": "none", "records": 42})
    return {"records": 42}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    with open("/app/dashboard.html", "r") as f:
        return f.read()


@app.get("/logs")
async def get_logs():
    import json

    lines = []
    try:
        log_paths = ["/app/app.log", "app/app.log", "app.log"]
        content = ""
        for path in log_paths:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if content:
                    break
            except Exception:
                continue
        for line in content.splitlines()[-200:]:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except Exception:
                lines.append({"message": line, "timestamp": "", "level": "INFO"})
    except Exception as e:
        lines.append({"message": "log read error: " + str(e), "timestamp": "", "level": "ERROR"})
    return {"lines": lines}


@app.post("/inject")
async def inject(type: str = "divide_by_zero"):
    import subprocess

    subprocess.Popen(["python", "inject_failure.py", "--type", type], cwd="/workspace")
    return {"status": "injected", "type": type}


@app.get("/report", response_class=HTMLResponse)
async def report():
    import json
    from pathlib import Path

    incidents = []
    try:
        log_paths = ["/app/app.log", "app/app.log"]
        content = ""
        for path in log_paths:
            try:
                content = Path(path).read_text(encoding="utf-8", errors="ignore")
                if content:
                    break
            except Exception:
                continue

        current = {}
        for line in content.splitlines():
            try:
                entry = json.loads(line.strip())
                msg = entry.get("message", "")
                rid = entry.get("request_id", "none")
                if rid == "none":
                    continue
                if msg == "CONSENSUS_REACHED":
                    current[rid] = {
                        "request_id": rid,
                        "started": entry.get("timestamp"),
                        "events": ["CONSENSUS_REACHED"],
                        "status": "IN_PROGRESS",
                    }
                elif rid in current:
                    current[rid]["events"].append(msg)
                    if msg == "PATCH_PROMOTED":
                        current[rid]["repair"] = "CODE_PATCH"
                    if msg == "CONTAINER_RESTARTED":
                        current[rid]["repair"] = "CONTAINER_RESTART"
                    if msg == "ESCALATION_REQUIRED":
                        current[rid]["status"] = "ESCALATED"
                        current[rid]["repair"] = "HUMAN_REQUIRED"
                    if msg == "HEALTH_CONFIRMED":
                        current[rid]["status"] = "RESOLVED"
                        current[rid]["resolved"] = entry.get("timestamp")
                    if "failure_class" in entry:
                        current[rid]["failure_class"] = entry.get("failure_class")
                        current[rid]["confidence"] = entry.get("confidence")
                        current[rid]["suspect_commit"] = entry.get("suspect_commit")
                    if msg == "FMG_FAST_PATH_FIRED":
                        current[rid]["fast_path"] = True
                    if msg == "SLACK_SENT":
                        current[rid]["slack"] = entry.get("status_code")
            except Exception:
                continue
        incidents = list(reversed(list(current.values())))[:20]
    except Exception as e:
        incidents = [{"error": str(e)}]

    rows = ""
    for inc in incidents:
        status = inc.get("status", "UNKNOWN")
        color = (
            "#00c851" if status == "RESOLVED" else "#ff4444" if status == "ESCALATED" else "#ffbb33"
        )
        fc = inc.get("failure_class", "UNKNOWN")
        conf = inc.get("confidence", "")
        conf_str = f"{conf:.0%}" if conf else ""
        repair = inc.get("repair", "")
        fast = "FMG FAST PATH" if inc.get("fast_path") else "GPT-4o"
        commit = inc.get("suspect_commit", "") or ""
        commit_short = commit[:40] if commit else "none"
        slack = f"Slack {inc.get('slack')}" if inc.get("slack") else ""
        events = " \u2192 ".join(inc.get("events", []))
        rows += f"""
        <tr>
          <td style="color:#00d4ff;font-family:monospace">{inc.get('request_id','')[:8]}</td>
          <td><span style="background:{color};color:#000;padding:3px 8px;border-radius:4px;font-weight:bold">{status}</span></td>
          <td style="color:#aa66cc">{fc}</td>
          <td>{conf_str}</td>
          <td style="color:#ffbb33">{repair}</td>
          <td style="color:#aaa;font-size:0.8em">{fast}</td>
          <td style="color:#888;font-size:0.75em;font-family:monospace">{commit_short}</td>
          <td style="color:#00c851;font-size:0.8em">{slack}</td>
          <td style="color:#555;font-size:0.7em">{inc.get('started','')[:19]}</td>
        </tr>
        <tr>
          <td colspan="9" style="color:#555;font-size:0.7em;font-family:monospace;padding:2px 10px 8px">{events}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>SHA Incident Report</title>
  <meta http-equiv="refresh" content="5">
  <style>
    body {{font-family:monospace;background:#0f0f1a;color:#eee;padding:20px;margin:0}}
    h1 {{color:#00d4ff;margin:0 0 5px 0}}
    .sub {{color:#666;margin-bottom:20px;font-size:0.9em}}
    table {{width:100%;border-collapse:collapse;background:#16213e}}
    th {{background:#1a1a3e;color:#00d4ff;padding:10px;text-align:left;font-size:0.85em}}
    td {{padding:8px 10px;border-bottom:1px solid #1a1a2e}}
    tr:hover td {{background:#1e2a4a}}
    .badge {{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.8em}}
  </style>
</head>
<body>
  <h1>Self-Healing Agent - Incident Report</h1>
  <div class="sub">Auto-refreshes every 5 seconds | {len(incidents)} incidents tracked</div>
  <table>
    <tr>
      <th>Request ID</th>
      <th>Status</th>
      <th>Failure Class</th>
      <th>Confidence</th>
      <th>Repair Action</th>
      <th>Diagnosis Path</th>
      <th>Suspect Commit</th>
      <th>Slack</th>
      <th>Started</th>
    </tr>
    {rows}
  </table>
</body>
</html>"""
    return html
