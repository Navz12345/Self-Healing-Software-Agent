from sequential_tuning.utils.json_eval import flat_field_f1, parse_json_safe, schema_compliant


def test_parse_json_safe_valid():
    valid, parsed, error = parse_json_safe('{"a": 1}')
    assert valid is True
    assert parsed == {"a": 1}
    assert error is None


def test_schema_compliant():
    assert schema_compliant({"name": "Ada", "done": False}, {"name": "string", "done": "boolean"})


def test_flat_field_f1():
    scores = flat_field_f1({"name": "Ada"}, {"name": "Ada"})
    assert scores["f1"] == 1.0
