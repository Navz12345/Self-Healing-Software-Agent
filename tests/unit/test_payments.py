try:
    from payments import process_transaction
except ImportError:
    from app.payments import process_transaction


def test_process_transaction_normal_case():
    assert process_transaction(100.0, 5) == {"result": 20.0, "status": "ok"}
