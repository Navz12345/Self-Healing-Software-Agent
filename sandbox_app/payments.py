from logger import get_logger

log = get_logger(__name__)


def process_transaction(amount: float, items: int) -> dict:
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )

    if items == 0:
        log.error(
            "PROCESS_TRANSACTION_ERROR", extra={"request_id": "none", "error": "Divide by zero"}
        )
        return {"result": None, "status": "error", "message": "Cannot divide by zero"}

    result = amount / items
    log.info("PROCESS_TRANSACTION_COMPLETE", extra={"request_id": "none", "result": result})
    return {"result": result, "status": "ok", "message": "Transaction processed successfully"}
