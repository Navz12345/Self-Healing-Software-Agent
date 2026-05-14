#!/bin/bash
set -e

KEY_EVENTS="CONSENSUS_REACHED|DIAGNOSIS_COMPLETE|PATCH_PROMOTED|CONTAINER_RESTARTED|FMG_FAST_PATH_FIRED|GPT4O_SKIPPED|ESCALATION_REQUIRED|HEALTH_CONFIRMED|SLACK_SENT"

show_summary() {
  local demo_name="$1"

  echo
  echo "=== Orchestrator summary: ${demo_name} ==="
  echo "Recent key events:"

  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "docker compose logs orchestrator | Select-String \"${KEY_EVENTS}\" | Select-Object -Last 15"
  elif command -v pwsh >/dev/null 2>&1; then
    pwsh -NoProfile -Command "docker compose logs orchestrator | Select-String \"${KEY_EVENTS}\" | Select-Object -Last 15"
  else
    docker compose logs orchestrator | grep -E "${KEY_EVENTS}" | tail -n 15 || true
  fi

  echo
  echo "Legend:"
  echo "- CONSENSUS_REACHED: both drones agreed the service is failing"
  echo "- DIAGNOSIS_COMPLETE failure_class=CODE_BUG: GPT-4o identified a code bug"
  echo "- DIAGNOSIS_COMPLETE failure_class=INFRA_CRASH: deterministic guard identified infrastructure outage"
  echo "- FMG_FAST_PATH_FIRED: system recognized the pattern from memory, skipped GPT-4o"
  echo "- GPT4O_SKIPPED: no API call was made, resolved from fingerprint memory"
  echo "- PATCH_PROMOTED: generated fix passed sandbox tests and was applied to production"
  echo "- CONTAINER_RESTARTED: orchestrator restarted the crashed container"
  echo "- HEALTH_CONFIRMED: health endpoint returned ok after recovery"
  echo "- ESCALATION_REQUIRED: confidence too low to act autonomously, human notified"
  echo "- SLACK_SENT status_code=200: real Slack notification delivered successfully"
  echo "- SLACK_SENT resolved=true: incident was fully resolved autonomously"
  echo "- SLACK_SENT resolved=false: incident escalated, human action required"
  echo
}

echo "=== Self-Healing Software Agent Demo ==="

echo "[1/3] Demo 1: Code Bug (divide-by-zero)"
curl -s http://localhost:8000/health | python -m json.tool
python inject_failure.py --type divide_by_zero
echo "Failure injected. Waiting for autonomous repair..."
sleep 50
curl -s http://localhost:8000/health | python -m json.tool
show_summary "Demo 1: Code Bug"
./scripts/restore_payments.sh

echo "[2/3] Demo 2: Infrastructure Crash"
python inject_failure.py --type infra_crash
echo "Container stopped. Waiting for DevOps agent to restart..."
sleep 45
curl -s http://localhost:8000/health | python -m json.tool
show_summary "Demo 2: Infrastructure Crash"
./scripts/restore_payments.sh

echo "[3/3] Demo 3: FMG Fast-Path (run divide-by-zero again)"
python inject_failure.py --type divide_by_zero
echo "Same failure injected. Should resolve in under 20s via FMG fast-path..."
sleep 22
curl -s http://localhost:8000/health | python -m json.tool
show_summary "Demo 3: FMG Fast-Path"
./scripts/restore_payments.sh

echo "=== Demo complete. Check Slack for notifications. ==="
