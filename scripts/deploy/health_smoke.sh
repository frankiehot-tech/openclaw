#!/bin/bash
# Minimal smoke test for health incident contract
set -e

echo "=== Health Incident Smoke Test ==="
echo "Running supervisor_daily_inspection.sh..."
bash /Volumes/1TB-M2/openclaw/scripts/supervisor_daily_inspection.sh

echo ""
echo "Verifying incident files..."
HEALTH_DIR="/Volumes/1TB-M2/openclaw/.openclaw/health"
EVENTS_DIR="$HEALTH_DIR/events"
INCIDENTS_DIR="$HEALTH_DIR/incidents"

if [[ ! -d "$EVENTS_DIR" ]] || [[ ! -d "$INCIDENTS_DIR" ]]; then
    echo "FAIL: events or incidents directory missing"
    exit 1
fi

LATEST="$EVENTS_DIR/latest.json"
if [[ ! -f "$LATEST" ]]; then
    echo "FAIL: latest.json not found"
    exit 1
fi

echo "Latest incident: $LATEST"
cat "$LATEST"

echo ""
echo "Validating JSON structure..."
python3 - <<'PY'
import json, sys, os
latest_path = "/Volumes/1TB-M2/openclaw/.openclaw/health/events/latest.json"
with open(latest_path, 'r') as f:
    data = json.load(f)
required = ['id', 'source', 'category', 'severity', 'summary', 'details', 'repairable', 'repair_flow', 'created_at']
for field in required:
    if field not in data:
        print(f"FAIL: missing field {field}")
        sys.exit(1)
print(f"SUCCESS: incident {data['id']} has category {data['category']}, repairable={data['repairable']}")
PY

echo ""
echo "Checking incident file count..."
INCIDENT_FILES=$(find "$INCIDENTS_DIR" -name "*.json" | wc -l)
echo "Total incident files: $INCIDENT_FILES"

echo ""
echo "Running multi-lane replay smoke test..."
if [[ -f "/Volumes/1TB-M2/openclaw/test_ai_plan_queue_runner_smoke.py" ]]; then
    cd /Volumes/1TB-M2/openclaw && python3 test_ai_plan_queue_runner_smoke.py 2>&1
    if [[ $? -eq 0 ]]; then
        echo "Multi-lane replay smoke test passed."
    else
        echo "Multi-lane replay smoke test failed."
        exit 1
    fi
else
    echo "Multi-lane replay smoke test script not found, skipping."
fi

echo ""
echo "=== Smoke test passed ==="