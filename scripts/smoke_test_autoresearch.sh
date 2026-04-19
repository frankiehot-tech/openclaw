#!/bin/bash
# Smoke test for Athena AutoResearch integration
# Verifies that the workflow entry works and outputs artifacts correctly.

set -e

cd "$(dirname "$0")/.."

echo "=== AutoResearch Smoke Test ==="
echo "Testing workflow entry and artifact generation..."

# Run a single AutoResearch cycle in dry-run mode
echo "1. Running AutoResearch cycle..."
python3 scripts/athena_autoresearch_runner.py run-once --dry-run

# Check that output files were created
echo "2. Checking output artifacts..."
if [ ! -d "workspace/autoresearch" ]; then
    echo "ERROR: workspace/autoresearch directory not found"
    exit 1
fi

# Find the latest research cycle JSON
latest_cycle=$(ls -t workspace/autoresearch/ares-*.json 2>/dev/null | head -1)
if [ -z "$latest_cycle" ]; then
    echo "ERROR: No research cycle JSON found"
    exit 1
fi

echo "   Found research cycle: $(basename "$latest_cycle")"

# Check for recommendation cards
if [ ! -d "workspace/autoresearch/recommendation_cards" ]; then
    echo "ERROR: recommendation_cards directory not found"
    exit 1
fi

card_count=$(ls workspace/autoresearch/recommendation_cards/*.json 2>/dev/null | wc -l)
echo "   Found $card_count recommendation card(s)"

# Validate JSON structure
echo "3. Validating JSON structure..."
python3 -c "
import json, sys
from pathlib import Path
try:
    with open('$latest_cycle') as f:
        data = json.load(f)
    if 'cycle_id' not in data:
        print('ERROR: Missing cycle_id in research result')
        sys.exit(1)
    print('   Research result JSON is valid')
    
    # Check at least one recommendation card
    cards_dir = Path('workspace/autoresearch/recommendation_cards')
    cards = list(cards_dir.glob('*.json')) if cards_dir.exists() else []
    if cards:
        with open(cards[0]) as f:
            card = json.load(f)
        if 'id' not in card or 'title' not in card:
            print('ERROR: Invalid recommendation card format')
            sys.exit(1)
        print('   Recommendation card JSON is valid')
    else:
        print('WARNING: No recommendation cards found')
except Exception as e:
    print(f'ERROR: JSON validation failed: {e}')
    sys.exit(1)
"

echo "4. Testing status command..."
python3 scripts/athena_autoresearch_runner.py status

echo "=== Smoke Test PASSED ==="
echo "AutoResearch workflow entry is functional."
echo "Output artifacts are being generated correctly."