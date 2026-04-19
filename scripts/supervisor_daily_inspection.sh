#!/bin/bash
# Health inspection script that outputs structured incidents with two problem categories.
# This script is part of the auto-repair chain reconnection.

set -e

RUNTIME_ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
HEALTH_DIR="$RUNTIME_ROOT/.openclaw/health"
EVENTS_DIR="$HEALTH_DIR/events"
INCIDENTS_DIR="$HEALTH_DIR/incidents"
mkdir -p "$EVENTS_DIR" "$INCIDENTS_DIR"

TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
INCIDENT_ID="m4-health-$TIMESTAMP"

# Function to check Athena runtime health
check_athena_runtime() {
    local pid_file="$RUNTIME_ROOT/.openclaw/athena_ai_plan_runner.pid"
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            echo "healthy"
        else
            echo "stale_pid"
        fi
    else
        echo "missing_pid"
    fi
}

# Function to check M4 health (simulated)
check_m4_health() {
    local state_file="$RUNTIME_ROOT/.openclaw/agent_state.json"
    if [[ -f "$state_file" ]]; then
        local size=$(wc -c < "$state_file" 2>/dev/null || echo 0)
        if [[ $size -gt 10 ]]; then
            echo "healthy"
        else
            echo "corrupted"
        fi
    else
        echo "missing"
    fi
}

# Perform checks
ATHENA_CHECK=$(check_athena_runtime)
M4_CHECK=$(check_m4_health)

# Determine incident category and severity based on checks
CATEGORY=""
SEVERITY="medium"
SUMMARY=""
DETAILS=""
REPAIRABLE=true
REPAIR_FLOW="athena_vscode_build"

if [[ "$ATHENA_CHECK" != "healthy" ]]; then
    CATEGORY="athena_runtime_problem"
    SUMMARY="Athena runtime state inconsistency detected"
    DETAILS=$(cat <<DET
{
    "check": "athena_pid",
    "status": "$ATHENA_CHECK",
    "pid_file": "$RUNTIME_ROOT/.openclaw/athena_ai_plan_runner.pid",
    "suggested_action": "restart Athena AI plan runner"
}
DET
)
    if [[ "$ATHENA_CHECK" == "missing_pid" ]]; then
        SEVERITY="high"
        REPAIRABLE=false
        REPAIR_FLOW="manual_intervention"
    fi
elif [[ "$M4_CHECK" != "healthy" ]]; then
    CATEGORY="m4_health_problem"
    SUMMARY="M4 health issue detected"
    DETAILS=$(cat <<DET
{
    "check": "agent_state",
    "status": "$M4_CHECK",
    "state_file": "$RUNTIME_ROOT/.openclaw/agent_state.json",
    "suggested_action": "verify agent state integrity"
}
DET
)
    if [[ "$M4_CHECK" == "missing" ]]; then
        SEVERITY="high"
        REPAIRABLE=false
        REPAIR_FLOW="manual_intervention"
    fi
else
    # No issues found - generate a healthy incident for completeness
    CATEGORY="healthy"
    SEVERITY="low"
    SUMMARY="All health checks passed"
    DETAILS="{}"
    REPAIRABLE=false
    REPAIR_FLOW="none"
fi

# Create incident JSON
cat > "$INCIDENTS_DIR/$INCIDENT_ID.json" <<EOF
{
  "id": "$INCIDENT_ID",
  "source": "supervisor_daily_inspection",
  "category": "$CATEGORY",
  "severity": "$SEVERITY",
  "summary": "$SUMMARY",
  "details": $DETAILS,
  "repairable": $REPAIRABLE,
  "repair_flow": "$REPAIR_FLOW",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Update latest.json for easy access
cp "$INCIDENTS_DIR/$INCIDENT_ID.json" "$EVENTS_DIR/latest.json"

echo "Generated incident: $INCIDENT_ID"
echo "Category: $CATEGORY"
echo "Severity: $SEVERITY"
echo "Repairable: $REPAIRABLE"
echo "Incident file: $INCIDENTS_DIR/$INCIDENT_ID.json"
echo "Latest snapshot: $EVENTS_DIR/latest.json"

# 自动触发修复路由（仅对可修复且非高风险 incident）
if [[ "$REPAIRABLE" == "true" && "$SEVERITY" != "high" ]]; then
    echo "检测到可修复 incident，尝试自动路由到修复通道..."
    echo "Incident ID: $INCIDENT_ID"
    echo "修复流程: $REPAIR_FLOW"
    
    # 调用自动修复路由器
    cd "$RUNTIME_ROOT" && python3 scripts/athena_auto_repair_router.py --latest 2>&1 | tee -a "$EVENTS_DIR/auto_route_$TIMESTAMP.log"
    ROUTE_RESULT=$?
    
    if [[ $ROUTE_RESULT -eq 0 ]]; then
        echo "✅ 修复任务创建成功"
    elif [[ $ROUTE_RESULT -eq 1 ]]; then
        echo "⚠️  修复任务创建失败或不需要创建"
    else
        echo "❌ 路由器执行异常，退出码: $ROUTE_RESULT"
    fi
else
    echo "跳过自动修复路由 (repairable=$REPAIRABLE, severity=$SEVERITY)"
fi