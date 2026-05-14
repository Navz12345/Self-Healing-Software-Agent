try:
    from payments import (
        calculate_discount,
        calculate_tax,
        process_transaction,
        process_transaction_with_tax,
        validate_transaction,
    )
except ImportError:
    from app.payments import (
        calculate_discount,
        calculate_tax,
        process_transaction,
        process_transaction_with_tax,
        validate_transaction,
    )


def test_process_transaction_normal_case():
    assert process_transaction(100.0, 5) == {"result": 20.0, "status": "ok"}


def test_validate_transaction_valid():
    result = validate_transaction(100.0, 5)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_transaction_zero_amount():
    result = validate_transaction(0, 5)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_transaction_zero_items():
    result = validate_transaction(100.0, 0)
    assert result["valid"] is False


def test_validate_transaction_exceeds_limit():
    result = validate_transaction(2_000_000, 5)
    assert result["valid"] is False


def test_calculate_tax_default_rate():
    assert calculate_tax(100.0) == 8.0


def test_calculate_tax_custom_rate():
    assert calculate_tax(200.0, 0.1) == 20.0


def test_calculate_tax_invalid_rate():
    import pytest

    with pytest.raises(ValueError):
        calculate_tax(100.0, 1.5)


def test_calculate_discount_no_discount():
    assert calculate_discount(100.0, 0) == 100.0


def test_calculate_discount_50_percent():
    assert calculate_discount(100.0, 50) == 50.0


def test_calculate_discount_invalid():
    import pytest

    with pytest.raises(ValueError):
        calculate_discount(100.0, 150)


def test_process_transaction_with_tax_normal():
    result = process_transaction_with_tax(100.0, 5)
    assert result["status"] == "ok"
    assert result["result"] == 20.0
    assert result["tax"] == 1.6
    assert result["total"] == 21.6


def test_process_transaction_with_tax_invalid():
    result = process_transaction_with_tax(0, 5)
    assert result["status"] == "error"
