#!/bin/bash
set -e
echo "=== Self-Healing Software Agent Demo ==="

echo "[1/3] Demo 1: Code Bug (divide-by-zero)"
curl -s http://localhost:8000/health | python -m json.tool
python inject_failure.py --type divide_by_zero
echo "Failure injected. Waiting for autonomous repair..."
sleep 50
curl -s http://localhost:8000/health | python -m json.tool

echo "[2/3] Demo 2: Infrastructure Crash"
python inject_failure.py --type infra_crash
echo "Container stopped. Waiting for DevOps agent to restart..."
sleep 45
curl -s http://localhost:8000/health | python -m json.tool

echo "[3/3] Demo 3: FMG Fast-Path (run divide-by-zero again)"
python inject_failure.py --type divide_by_zero
echo "Same failure injected. Should resolve in under 20s via FMG fast-path..."
sleep 22
curl -s http://localhost:8000/health | python -m json.tool

echo "=== Demo complete. Check Slack for notifications. ==="
