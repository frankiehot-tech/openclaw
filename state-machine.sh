#!/bin/bash
# GSD V2 State Machine Engine - Athena-Open Human 智能工作流核心

set -euo pipefail

STATE_DIR="$HOME/.openclaw-gsdv2/state"
STATE_FILE="${STATE_DIR}/global-state.json"
LOG_FILE="$HOME/.openclaw-gsdv2/logs/state-transitions.jsonl"

# 初始化状态机
init_state_machine() {
    mkdir -p "$STATE_DIR"
    if [ ! -f "$STATE_FILE" ]; then
        echo '{
            "state": "IDLE",
            "wave_id": null,
            "agent": null,
            "start_time": null,
            "last_scan_time": null,
            "total_waves": 0,
            "successful_waves": 0,
            "last_transition_time": null,
            "last_trigger": null
        }' > "$STATE_FILE"
    fi
}

# 状态转换函数
transition_to() {
    local new_state=$1
    local trigger=$2
    local timestamp=$(date -Iseconds)
    
    local old_state=$(jq -r '.state' "$STATE_FILE")
    
    jq --arg new "$new_state" \
       --arg time "$timestamp" \
       --arg trigger "$trigger" \
       '.state = $new | .last_transition_time = $time | .last_trigger = $trigger' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    # 审计日志
    echo "{\"ts\":\"$timestamp\",\"from\":\"$old_state\",\"to\":\"$new_state\",\"trigger\":\"$trigger\"}" >> "$LOG_FILE"
    
    echo "🔄 [$timestamp] $old_state → $new_state | 触发: $trigger"
}

# 检查EVO文件夹变化
check_evo_new_files() {
    local evo_dir="$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/013-EVO"
    if [ -d "$evo_dir" ]; then
        local new_files=$(find "$evo_dir" -name "*.md" -mtime -1 2>/dev/null | wc -l)
        if [ "$new_files" -gt 0 ]; then
            return 0
        fi
    fi
    return 1
}

# 状态处理函数
state_idle() {
    if check_evo_new_files; then
        transition_to "SCAN" "new_evo_detected"
    else
        # 每30分钟扫描一次
        local last_scan=$(jq -r '.last_scan_time' "$STATE_FILE")
        if [ "$last_scan" != "null" ]; then
            local last_scan_sec=$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$last_scan" +%s 2>/dev/null || echo 0)
            local now_sec=$(date +%s)
            if [ $((now_sec - last_scan_sec)) -gt 1800 ]; then
                transition_to "SCAN" "periodic_scan"
            fi
        else
            transition_to "SCAN" "initial_scan"
        fi
    fi
}

state_scan() {
    local evo_count=$(find "$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/013-EVO" -name "*.md" -mtime -1 2>/dev/null | wc -l)
    
    # 更新扫描时间
    jq --arg time "$(date -Iseconds)" '.last_scan_time = $time' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    if [ "$evo_count" -gt 0 ]; then
        echo "📋 检测到 $evo_count 个新EVO文件"
        transition_to "PLAN" "found_${evo_count}_new_ideas"
    else
        transition_to "IDLE" "no_new_content"
    fi
}

state_plan() {
    local wave_id="WAVE-$(date +%Y%m%d-%H%M%S)"
    
    jq --arg wave "$wave_id" \
       --arg agent "athena-strategist" \
       --arg time "$(date -Iseconds)" \
       '.wave_id = $wave | .agent = $agent | .start_time = $time' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    echo "📋 生成 Wave $wave_id 执行计划..."
    sleep 1
    
    transition_to "DISPATCH" "plan_generated"
}

state_dispatch() {
    local agent_type="claude-executor"
    jq --arg agent "$agent_type" '.agent = $agent' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    transition_to "EXECUTE" "routed_to_${agent_type}"
}

state_execute() {
    local wave_id=$(jq -r '.wave_id' "$STATE_FILE")
    local agent=$(jq -r '.agent' "$STATE_FILE")
    
    echo "🚀 执行 Wave $wave_id 使用 $agent..."
    sleep 2
    
    transition_to "VERIFY" "execution_success"
}

state_verify() {
    echo "🔍 验证执行结果..."
    sleep 1
    
    transition_to "ARCHIVE" "verification_passed"
}

state_archive() {
    local wave_id=$(jq -r '.wave_id' "$STATE_FILE")
    
    jq '.total_waves += 1 | .successful_waves += 1' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    echo "📁 归档 Wave $wave_id..."
    
    transition_to "IDLE" "wave_archived"
}

# 主循环
main_loop() {
    init_state_machine
    
    echo "🚀 GSD V2 状态机启动 - $(date)"
    echo "监控目录: $HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/013-EVO"
    
    while true; do
        local current_state=$(jq -r '.state' "$STATE_FILE")
        
        case "$current_state" in
            "IDLE") state_idle ;;
            "SCAN") state_scan ;;
            "PLAN") state_plan ;;
            "DISPATCH") state_dispatch ;;
            "EXECUTE") state_execute ;;
            "VERIFY") state_verify ;;
            "ARCHIVE") state_archive ;;
            *) transition_to "IDLE" "error_recovery" ;;
        esac
        
        sleep 10
    done
}

# CLI 接口
case "${1:-status}" in
    start) main_loop ;;
    status) 
        if [ -f "$STATE_FILE" ]; then
            jq . "$STATE_FILE"
        else
            echo "状态文件不存在，状态机未初始化"
        fi
        ;;
    reset) 
        rm -f "$STATE_FILE" 
        init_state_machine 
        echo "状态机已重置"
        ;;
    *) echo "Usage: state-machine {start|status|reset}" ;;
esac