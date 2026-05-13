from logger import get_logger

log = get_logger(__name__)

def process_transaction(amount: float, items: int, request_id: str = "none") -> dict:
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": request_id, "amount": amount, "items": items},
    )
    
    if items == 0:
        log.error("DIVIDE_BY_ZERO_ERROR", extra={"request_id": request_id, "amount": amount, "items": items})
        return {"result": None, "status": "error", "message": "Cannot divide by zero"}
    
    result = amount / items
    log.info("PROCESS_TRANSACTION_COMPLETE", extra={"request_id": request_id, "result": result})
    return {"result": result, "status": "ok"}