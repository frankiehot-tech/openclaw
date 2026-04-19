#!/bin/bash
# GSD V2 Phase 1 基础架构准备脚本

set -euo pipefail

# 配置参数
BASE_DIR="$HOME/.openclaw"
LOG_DIR="/Volumes/1TB-M2/openclaw/workspace/gsd_v2_preparation"
TIMESTAMP=$(date -Iseconds)

echo "🚀 GSD V2 Phase 1 基础架构准备开始..."
echo "============================================"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 记录开始时间
echo "开始时间: $TIMESTAMP" > "$LOG_DIR/phase1_start.log"

# 1. 创建GSD V2核心目录结构
echo "📁 创建GSD V2核心目录结构..."

directories=(
    "core"
    "config" 
    "workflows"
    "agents"
    "hooks"
    "logs"
    "state"
    "checkpoints"
)

for dir in "${directories[@]}"; do
    mkdir -p "$BASE_DIR/$dir"
    echo "✅ 创建目录: $BASE_DIR/$dir"
done

# 2. 设置目录权限
echo "🔐 设置目录权限..."
chmod 755 "$BASE_DIR"
chmod 700 "$BASE_DIR/state" "$BASE_DIR/checkpoints"
chmod 755 "$BASE_DIR/core" "$BASE_DIR/config" "$BASE_DIR/workflows"

# 3. 创建基础配置文件
echo "⚙️ 创建基础配置文件..."

# 版本文件
cat > "$BASE_DIR/version.json" << EOF
{
    "version": "gsd_v2_1.0",
    "created_at": "$TIMESTAMP",
    "phase": "phase1_foundation",
    "status": "initializing"
}
EOF

# 基础配置
cat > "$BASE_DIR/config/base_config.yaml" << EOF
# GSD V2 基础配置
version: "1.0"
created_at: "$TIMESTAMP"

system:
  name: "Athena Open Human GSD V2"
  description: "基于GSD V2架构的智能实施系统"
  
states:
  - "IDLE"
  - "SCAN" 
  - "PLAN"
  - "DISPATCH"
  - "EXECUTE"
  - "VERIFY"
  - "EVOLVE"
  - "ARCHIVE"

logging:
  level: "INFO"
  audit_enabled: true
  retention_days: 30
EOF

# 4. 创建状态机引擎基础框架
echo "🔄 创建状态机引擎基础框架..."

cat > "$BASE_DIR/core/state-machine.sh" << 'EOF'
#!/bin/bash
# GSD V2 State Machine Engine v1.0

set -euo pipefail

# 配置路径
STATE_DIR="$HOME/.openclaw/state"
STATE_FILE="$STATE_DIR/global-state.json"
LOG_FILE="$HOME/.openclaw/logs/state-transitions.jsonl"

# GSD V2 状态定义
STATES=("IDLE" "SCAN" "PLAN" "DISPATCH" "EXECUTE" "VERIFY" "EVOLVE" "ARCHIVE")
CURRENT_STATE="IDLE"

# 初始化状态机
init_state_machine() {
    mkdir -p "$STATE_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    if [ ! -f "$STATE_FILE" ]; then
        cat > "$STATE_FILE" << STATE_EOF
{
    "state": "IDLE",
    "wave_id": null,
    "agent": null,
    "start_time": null,
    "checkpoint": null,
    "attempts": 0,
    "version": "gsd_v2_1.0"
}
STATE_EOF
    fi
    
    CURRENT_STATE=$(jq -r '.state' "$STATE_FILE" 2>/dev/null || echo "IDLE")
}

# 状态转换函数（带审计日志）
transition_to() {
    local new_state="$1"
    local trigger="$2"
    local metadata="${3:-{}}"
    local timestamp=$(date -Iseconds)
    
    local old_state="$CURRENT_STATE"
    
    # 验证状态转换合法性
    if ! validate_transition "$old_state" "$new_state"; then
        echo "❌ 非法状态转换: $old_state -> $new_state"
        return 1
    fi
    
    # 更新状态文件
    jq --arg new "$new_state" \
       --arg time "$timestamp" \
       --arg trigger "$trigger" \
       --argjson metadata "$metadata" \
       '.state = $new | .transition_time = $time | .trigger = $trigger | .metadata = $metadata' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    CURRENT_STATE="$new_state"
    
    # 记录审计日志
    local audit_entry="{\"timestamp\":\"$timestamp\",\"old_state\":\"$old_state\",\"new_state\":\"$new_state\",\"trigger\":\"$trigger\",\"metadata\":$metadata}"
    echo "$audit_entry" >> "$LOG_FILE"
    
    echo "✅ 状态转换: $old_state -> $new_state (触发: $trigger)"
}

# 验证状态转换合法性
validate_transition() {
    local old_state="$1"
    local new_state="$2"
    
    # GSD V2: 严格有序的状态转换规则
    case "$old_state" in
        "IDLE") [[ "$new_state" == "SCAN" ]] ;;
        "SCAN") [[ "$new_state" == "PLAN" || "$new_state" == "IDLE" ]] ;;
        "PLAN") [[ "$new_state" == "DISPATCH" || "$new_state" == "SCAN" ]] ;;
        "DISPATCH") [[ "$new_state" == "EXECUTE" || "$new_state" == "PLAN" ]] ;;
        "EXECUTE") [[ "$new_state" == "VERIFY" || "$new_state" == "DISPATCH" ]] ;;
        "VERIFY") [[ "$new_state" == "EVOLVE" || "$new_state" == "EXECUTE" ]] ;;
        "EVOLVE") [[ "$new_state" == "ARCHIVE" || "$new_state" == "VERIFY" ]] ;;
        "ARCHIVE") [[ "$new_state" == "IDLE" ]] ;;
        *) false ;;
    esac
}

# 获取当前状态
get_current_state() {
    echo "$CURRENT_STATE"
}

# 显示状态信息
show_status() {
    echo "📊 GSD V2 状态机状态"
    echo "===================="
    echo "当前状态: $CURRENT_STATE"
    
    if [ -f "$STATE_FILE" ]; then
        echo "状态文件: $STATE_FILE"
        echo "内容:"
        jq . "$STATE_FILE" 2>/dev/null || cat "$STATE_FILE"
    fi
    
    if [ -f "$LOG_FILE" ]; then
        echo "审计日志条目数: $(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)"
    fi
}

# 主函数
main() {
    case "${1:-show}" in
        "init")
            init_state_machine
            ;;
        "transition")
            init_state_machine
            if [ $# -ge 3 ]; then
                transition_to "$2" "$3" "${4:-{}}"
            else
                echo "用法: $0 transition <新状态> <触发原因> [元数据]"
                exit 1
            fi
            ;;
        "status")
            init_state_machine
            show_status
            ;;
        "show")
            init_state_machine
            show_status
            ;;
        *)
            echo "用法: $0 {init|transition|status|show}"
            exit 1
            ;;
    esac
}

# 如果直接执行，调用主函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
EOF

# 设置执行权限
chmod +x "$BASE_DIR/core/state-machine.sh"

# 5. 创建基础工作流定义
echo "📋 创建基础工作流定义..."

cat > "$BASE_DIR/workflows/phase1_foundation.yml" << EOF
# GSD V2 Phase 1 基础架构工作流
version: "1.0"
phase: "phase1_foundation"
created_at: "$TIMESTAMP"

tasks:
  - id: "setup_directories"
    name: "创建目录结构"
    description: "创建GSD V2核心目录结构"
    status: "completed"
    
  - id: "setup_permissions" 
    name: "设置权限"
    description: "设置目录和文件权限"
    status: "completed"
    
  - id: "create_configs"
    name: "创建配置文件"
    description: "创建基础配置文件"
    status: "completed"
    
  - id: "implement_state_machine"
    name: "实现状态机引擎"
    description: "开发状态机引擎基础框架"
    status: "completed"
    
  - id: "create_workflows"
    name: "创建工作流定义"
    description: "创建基础工作流定义"
    status: "completed"
    
  - id: "validation_test"
    name: "验证测试"
    description: "验证Phase 1实施结果"
    status: "pending"

success_criteria:
  - "所有目录结构创建完成"
  - "状态机引擎可正常执行"
  - "基础配置文件就绪"
  - "工作流定义完整"

next_phase: "phase2_core_integration"
EOF

# 6. 创建验证脚本
echo "🧪 创建验证脚本..."

cat > "$BASE_DIR/core/validate_phase1.sh" << 'EOF'
#!/bin/bash
# GSD V2 Phase 1 验证脚本

set -euo pipefail

BASE_DIR="$HOME/.openclaw"
VALIDATION_RESULTS=()

echo "🔍 开始GSD V2 Phase 1 验证..."

# 验证目录结构
echo "📁 验证目录结构..."
required_dirs=("core" "config" "workflows" "agents" "hooks" "logs" "state" "checkpoints")

for dir in "${required_dirs[@]}"; do
    if [ -d "$BASE_DIR/$dir" ]; then
        VALIDATION_RESULTS+=("✅ $dir 目录存在")
    else
        VALIDATION_RESULTS+=("❌ $dir 目录缺失")
    fi
done

# 验证状态机引擎
echo "🔄 验证状态机引擎..."
if [ -x "$BASE_DIR/core/state-machine.sh" ]; then
    # 测试状态机初始化
    if "$BASE_DIR/core/state-machine.sh" init > /dev/null 2>&1; then
        VALIDATION_RESULTS+=("✅ 状态机引擎可执行")
    else
        VALIDATION_RESULTS+=("❌ 状态机引擎执行失败")
    fi
    
    # 测试状态转换
    if "$BASE_DIR/core/state-machine.sh" transition SCAN "phase1_validation" '{"test": true}' > /dev/null 2>&1; then
        VALIDATION_RESULTS+=("✅ 状态转换功能正常")
    else
        VALIDATION_RESULTS+=("❌ 状态转换功能异常")
    fi
else
    VALIDATION_RESULTS+=("❌ 状态机引擎文件不存在或不可执行")
fi

# 验证配置文件
echo "⚙️ 验证配置文件..."
required_configs=("version.json" "config/base_config.yaml" "workflows/phase1_foundation.yml")

for config in "${required_configs[@]}"; do
    if [ -f "$BASE_DIR/$config" ]; then
        VALIDATION_RESULTS+=("✅ $config 配置文件存在")
    else
        VALIDATION_RESULTS+=("❌ $config 配置文件缺失")
    fi
done

# 输出验证结果
echo ""
echo "📊 Phase 1 验证结果:"
echo "===================="

for result in "${VALIDATION_RESULTS[@]}"; do
    echo "$result"
done

# 计算通过率
total_checks=${#VALIDATION_RESULTS[@]}
passed_checks=$(printf '%s\n' "${VALIDATION_RESULTS[@]}" | grep -c "✅" || true)

if [ "$total_checks" -gt 0 ]; then
    pass_rate=$((passed_checks * 100 / total_checks))
    echo ""
    echo "📈 通过率: $pass_rate% ($passed_checks/$total_checks)"
    
    if [ "$pass_rate" -eq 100 ]; then
        echo "🎉 Phase 1 验证通过!"
        exit 0
    else
        echo "⚠️ Phase 1 验证未完全通过"
        exit 1
    fi
else
    echo "❌ 验证检查失败"
    exit 1
fi
EOF

chmod +x "$BASE_DIR/core/validate_phase1.sh"

# 7. 更新版本文件状态
echo "📝 更新实施状态..."
jq '.status = "completed" | .completed_at = "'$TIMESTAMP'"' "$BASE_DIR/version.json" > "$BASE_DIR/version.json.tmp"
mv "$BASE_DIR/version.json.tmp" "$BASE_DIR/version.json"

# 8. 记录完成时间
echo "完成时间: $(date -Iseconds)" > "$LOG_DIR/phase1_complete.log"

# 9. 运行验证
echo "🔍 运行Phase 1验证..."
"$BASE_DIR/core/validate_phase1.sh"

# 10. 生成实施报告
echo "📋 生成实施报告..."

cat > "$LOG_DIR/phase1_implementation_report.md" << EOF
# GSD V2 Phase 1 基础架构实施报告

**实施时间**: $TIMESTAMP  
**实施状态**: 已完成  
**验证结果**: 待验证

## 📊 实施内容汇总

### 已完成的组件

#### 1. 目录结构
- ✅ 核心目录: core/
- ✅ 配置目录: config/  
- ✅ 工作流目录: workflows/
- ✅ Agent目录: agents/
- ✅ 钩子目录: hooks/
- ✅ 日志目录: logs/
- ✅ 状态目录: state/
- ✅ 检查点目录: checkpoints/

#### 2. 状态机引擎
- ✅ 状态机脚本: core/state-machine.sh
- ✅ 状态定义: IDLE→SCAN→PLAN→DISPATCH→EXECUTE→VERIFY→EVOLVE→ARCHIVE
- ✅ 审计日志: 自动记录状态转换

#### 3. 配置文件
- ✅ 版本文件: version.json
- ✅ 基础配置: config/base_config.yaml
- ✅ 工作流定义: workflows/phase1_foundation.yml

#### 4. 验证工具
- ✅ 验证脚本: core/validate_phase1.sh
- ✅ 权限设置: 目录权限已配置

## 🚀 下一步行动

### Phase 2 准备
1. **核心组件集成**: 审计日志、模型配置、容错机制
2. **AIplan集成**: 建立智能跟进系统
3. **工作流迁移**: 开始迁移现有工作流

### 立即行动
- 运行验证脚本确认实施结果
- 准备Phase 2实施环境
- 配置AIplan跟踪任务

## 📁 文件位置

- **GSD V2根目录**: $BASE_DIR
- **实施日志**: $LOG_DIR
- **状态机引擎**: $BASE_DIR/core/state-machine.sh
- **验证脚本**: $BASE_DIR/core/validate_phase1.sh

---

**报告生成时间**: $(date -Iseconds)
EOF

echo ""
echo "🎉 GSD V2 Phase 1 基础架构准备完成!"
echo "============================================"
echo "📁 GSD V2根目录: $BASE_DIR"
echo "📋 实施报告: $LOG_DIR/phase1_implementation_report.md"
echo "🔍 验证脚本: $BASE_DIR/core/validate_phase1.sh"
echo ""
echo "🚀 下一步: 运行验证脚本确认实施结果，准备Phase 2实施"