from logger import get_logger

log = get_logger(__name__)
_call_count = 0

def process_transaction(amount: float, items: int) -> dict:
    global _call_count
    _call_count += 1
    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )
    if _call_count in {1, 4}:
        raise ValueError("intermittent_failure")
    
    if items == 0:
        log.error("Division by zero error", extra={"request_id": "none", "amount": amount, "items": items})
        return {"result": None, "status": "error", "message": "Cannot divide by zero"}
    
    return {"result": amount / items, "status": "ok"}