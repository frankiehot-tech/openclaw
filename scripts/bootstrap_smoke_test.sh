#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/bootstrap_smoke_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Bootstrap Smoke Test $(date) ==="

runners=(
    "athena_ai_plan_runner"
    "codex_review_runner" 
    "codex_plan_runner"
)

run_status() {
    local runner=$1
    "$ROOT/scripts/status_${runner}.sh"
}

run_start() {
    local runner=$1
    "$ROOT/scripts/start_${runner}.sh"
}

run_stop() {
    local runner=$1
    "$ROOT/scripts/stop_${runner}.sh"
}

test_runner() {
    local runner=$1
    echo "--- Testing $runner ---"
    
    # Step 1: Ensure stopped
    echo "Stopping $runner if running..."
    run_stop "$runner" >/dev/null 2>&1 || true
    sleep 2
    
    # Step 2: Check status shows stopped
    if run_status "$runner" >/dev/null 2>&1; then
        echo "FAIL: $runner still running after stop"
        return 1
    fi
    echo "OK: $runner stopped"
    
    # Step 3: Start runner
    echo "Starting $runner..."
    start_output=$(run_start "$runner")
    echo "Start output: $start_output"
    sleep 2
    
    # Step 4: Verify status shows running
    if ! run_status "$runner" >/dev/null 2>&1; then
        echo "FAIL: $runner not running after start"
        return 1
    fi
    echo "OK: $runner running"
    
    # Step 5: Try to start again (should exit 0 with PID)
    echo "Attempting duplicate start..."
    dup_output=$(run_start "$runner")
    echo "Duplicate start output: $dup_output"
    # Should not have started new process; just output PID
    
    # Step 6: Stop runner
    echo "Stopping $runner..."
    stop_output=$(run_stop "$runner")
    echo "Stop output: $stop_output"
    sleep 2
    
    # Step 7: Verify stopped
    if run_status "$runner" >/dev/null 2>&1; then
        echo "FAIL: $runner still running after stop"
        return 1
    fi
    echo "OK: $runner stopped after stop"
    
    # Step 8: Restart after stop
    echo "Restarting $runner..."
    restart_output=$(run_start "$runner")
    echo "Restart output: $restart_output"
    sleep 2
    
    if ! run_status "$runner" >/dev/null 2>&1; then
        echo "FAIL: $runner not running after restart"
        return 1
    fi
    echo "OK: $runner running after restart"
    
    # Final cleanup
    run_stop "$runner" >/dev/null 2>&1 || true
    sleep 1
    echo "--- $runner test passed ---"
    return 0
}

overall_result=0
for runner in "${runners[@]}"; do
    if test_runner "$runner"; then
        echo "PASS: $runner"
    else
        echo "FAIL: $runner"
        overall_result=1
    fi
done

echo "=== Smoke test completed with exit code $overall_result ==="
exit $overall_result