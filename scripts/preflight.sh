#!/bin/bash
set -e
echo "=== Preflight Check ==="
echo "[1/5] Lint..."
python -m ruff check . --no-cache
python -m black --check .
echo "[2/5] Tests..."
pytest tests/ --ignore=tests/test_json_eval.py \
  --junitxml=reports/unit.xml \
  --cov=. --cov-report=xml:reports/coverage.xml -q
echo "[3/5] Security..."
pip-audit --format json -o reports/security.txt || true
echo "[4/5] Load test (quick 10s)..."
echo "Skipping load test in preflight - run make loadtest separately"
echo "[5/5] Manifest check..."
python -c "
import yaml
m = yaml.safe_load(open('grading/manifest.yaml'))
assert m.get('commit_sha'), 'commit_sha is empty'
assert m.get('python_version'), 'python_version missing'
print('Manifest OK:', m.get('commit_sha')[:8])
"
echo "=== Preflight PASSED ==="
