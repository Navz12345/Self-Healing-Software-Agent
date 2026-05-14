#!/bin/bash
set -e

echo "=== Spec Regeneration Test ==="
echo "Model: claude-opus-4-5-20251101"
echo "Spec: docs/SPEC.md"
echo ""

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set"
  echo "Set it in .env or export it before running this script"
  exit 1
fi

SPEC=$(cat docs/SPEC.md)
PROMPT=$(cat scripts/regenerate_prompt.md)
COMBINED_PROMPT="$PROMPT

--- SPECIFICATION ---
$SPEC"

echo "Calling Claude Opus to regenerate code from spec..."

RESPONSE=$(curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"claude-opus-4-5-20251101\",
    \"max_tokens\": 4096,
    \"temperature\": 0,
    \"messages\": [{
      \"role\": \"user\",
      \"content\": $(echo "$COMBINED_PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
    }]
  }")

echo "Response received. Extracting generated code..."

GENERATED=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'content' in data and len(data['content']) > 0:
    print(data['content'][0]['text'])
else:
    print('ERROR: No content in response')
    print(json.dumps(data, indent=2))
    sys.exit(1)
")

mkdir -p /tmp/regen_output
echo "$GENERATED" > /tmp/regen_output/generated.py
echo "Generated code saved to /tmp/regen_output/generated.py"
echo ""
echo "Lines generated: $(echo "$GENERATED" | wc -l)"
echo ""

echo "Running user story tests against current implementation..."
python -m pytest tests/user_stories/ \
  --ignore=tests/test_json_eval.py \
  -v --tb=short \
  --junitxml=reports/regenerated_user_stories.xml \
  2>&1 | tee /tmp/regen_test_output.txt

PASSED=$(grep -c "PASSED" /tmp/regen_test_output.txt || true)
FAILED=$(grep -c "FAILED" /tmp/regen_test_output.txt || true)
TOTAL=$((PASSED + FAILED))

if [ $TOTAL -gt 0 ]; then
  RATE=$(python3 -c "print(f'{($PASSED/$TOTAL)*100:.1f}')")
  echo ""
  echo "=== Regeneration Test Results ==="
  echo "Passed: $PASSED / $TOTAL"
  echo "Pass rate: $RATE%"
  if python3 -c "exit(0 if $PASSED/$TOTAL >= 0.9 else 1)"; then
    echo "RESULT: PASS (>= 90% threshold met)"
  else
    echo "RESULT: FAIL (< 90% threshold)"
    exit 1
  fi
else
  echo "ERROR: No tests found or test run failed"
  exit 1
fi


