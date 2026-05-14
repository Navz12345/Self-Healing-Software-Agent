from logger import get_logger

log = get_logger(__name__)


def process_transaction(amount: float, items: int) -> dict:
    try:
        if items == 0:
            raise ValueError("Number of items cannot be zero.")
        result = amount / items
        log.info("PROCESS_TRANSACTION_COMPLETE", extra={"request_id": "none", "result": result})
        return {"result": result, "status": "ok"}
    except ZeroDivisionError:
        log.error(
            "PROCESS_TRANSACTION_FAILED",
            extra={"request_id": "none", "error": "Division by zero error"},
        )
        return {"result": None, "status": "error", "error": "Division by zero"}
    except Exception as e:
        log.error("PROCESS_TRANSACTION_FAILED", extra={"request_id": "none", "error": str(e)})
        return {"result": None, "status": "error", "error": str(e)}


def validate_transaction(amount: float, items: int) -> dict:
    """Validate transaction inputs before processing."""
    errors = []
    if amount <= 0:
        errors.append("Amount must be greater than zero")
    if items <= 0:
        errors.append("Items must be greater than zero")
    if amount > 1_000_000:
        errors.append("Amount exceeds maximum transaction limit")
    if items > 10_000:
        errors.append("Items exceeds maximum order size")
    return {"valid": len(errors) == 0, "errors": errors}


def calculate_tax(amount: float, tax_rate: float = 0.08) -> float:
    """Calculate tax for a transaction."""
    if tax_rate < 0 or tax_rate > 1:
        raise ValueError("Tax rate must be between 0 and 1")
    return round(amount * tax_rate, 2)


def calculate_discount(amount: float, discount_pct: float = 0.0) -> float:
    """Apply a percentage discount to an amount."""
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount must be between 0 and 100")
    return round(amount * (1 - discount_pct / 100), 2)


def process_transaction_with_tax(amount: float, items: int, tax_rate: float = 0.08) -> dict:
    """Process a transaction and include tax calculation."""
    validation = validate_transaction(amount, items)
    if not validation["valid"]:
        log.error(
            "TRANSACTION_VALIDATION_FAILED",
            extra={"request_id": "none", "errors": validation["errors"]},
        )
        return {"result": None, "status": "error", "errors": validation["errors"]}
    base = amount / items
    tax = calculate_tax(base, tax_rate)
    total = round(base + tax, 2)
    log.info(
        "PROCESS_TRANSACTION_WITH_TAX_COMPLETE",
        extra={"request_id": "none", "base": base, "tax": tax, "total": total},
    )
    return {"result": base, "tax": tax, "total": total, "status": "ok"}
