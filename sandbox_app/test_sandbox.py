import sys

sys.path.insert(0, "/app")
from payments import process_transaction


def test_process_transaction_normal_case():
    result = process_transaction(100.0, 5)
    assert result == {"result": 20.0, "status": "ok"}
