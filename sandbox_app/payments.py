from logger import get_logger

log = get_logger(__name__)


def process_transaction(amount: float, items: int) -> dict:
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )
    result = amount / items
    log.info(
        "PROCESS_TRANSACTION_COMPLETE",
        extra={"request_id": "none", "result": result},
    )
    return {"result": result, "status": "ok"}
