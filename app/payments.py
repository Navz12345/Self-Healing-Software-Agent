from logger import get_logger

log = get_logger(__name__)


def process_transaction(amount: float, items: int) -> dict:
    if items == 0:
        log.error(
            "PROCESS_TRANSACTION_ERROR",
            extra={
                "request_id": "none",
                "amount": amount,
                "items": items,
                "error": "Division by zero",
            },
        )
        return {"result": None, "status": "error", "error": "Division by zero"}

    log.info(
        "PROCESS_TRANSACTION_STARTED",
        extra={"request_id": "none", "amount": amount, "items": items},
    )

    try:
        result = amount / items
    except ZeroDivisionError:
        log.error(
            "PROCESS_TRANSACTION_ERROR",
            extra={
                "request_id": "none",
                "amount": amount,
                "items": items,
                "error": "Division by zero",
            },
        )
        return {"result": None, "status": "error", "error": "Division by zero"}
    except Exception as e:
        log.error(
            "PROCESS_TRANSACTION_ERROR",
            extra={"request_id": "none", "amount": amount, "items": items, "error": str(e)},
        )
        return {"result": None, "status": "error", "error": str(e)}

    log.info(
        "PROCESS_TRANSACTION_COMPLETED",
        extra={"request_id": "none", "amount": amount, "items": items, "result": result},
    )

    return {"result": result, "status": "ok"}
