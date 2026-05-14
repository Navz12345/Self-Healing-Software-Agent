import time
from pathlib import Path

from fastapi import FastAPI, Request

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
