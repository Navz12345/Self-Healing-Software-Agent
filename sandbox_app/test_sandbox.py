import sys

sys.path.insert(0, "/app")
from payments import (
    calculate_discount,
    calculate_tax,
    process_transaction,
    process_transaction_with_tax,
    validate_transaction,
)


def test_process_transaction_normal_case():
    result = process_transaction(100.0, 5)
    assert result == {"result": 20.0, "status": "ok"}


def test_validate_transaction_valid():
    result = validate_transaction(100.0, 5)
    assert result["valid"] is True


def test_calculate_tax_default():
    assert calculate_tax(100.0) == 8.0


def test_calculate_discount_zero():
    assert calculate_discount(100.0, 0) == 100.0


def test_process_transaction_with_tax():
    result = process_transaction_with_tax(100.0, 5)
    assert result["status"] == "ok"
