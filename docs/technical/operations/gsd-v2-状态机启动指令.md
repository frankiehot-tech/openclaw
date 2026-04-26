# GSD V2 状态机启动与监控指令

**制定时间**: 2026-04-09  
**目标**: 立即启动GSD V2状态机，保障Athena-Open Human智能工作流稳定运行  
**监控机制**: 每日7点自动报告

## 🚀 **立即执行指令**

### **第一步：创建GSD V2核心架构**

```bash
# 1. 创建GSD V2目录结构
mkdir -p ~/.openclaw-gsdv2/{core,config,agents,hooks,workflows,logs,state}

# 2. 创建状态机引擎（基于GSD V2实施方案）
cat > ~/.openclaw-gsdv2/core/state-machine.sh << 'EOF'
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
        echo '{"state":"IDLE","wave_id":null,"agent":null,"start_time":null}' > "$STATE_FILE"
    fi
}

# 主循环
main_loop() {
    init_state_machine
    echo "🚀 GSD V2 状态机启动 - $(date)"
    
    while true; do
        # 监控EVO文件夹变化
        local evo_count=$(find "$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/013-EVO" -name "*.md" -mtime -1 2>/dev/null | wc -l)
        
        if [ "$evo_count" -gt 0 ]; then
            echo "📋 检测到 $evo_count 个新EVO文件，触发执行流程"
            # 这里应该触发实际的执行流程
        fi
        
        sleep 30
    done
}

case "${1:-status}" in
    start) main_loop ;;
    status) echo "GSD V2状态机就绪" ;;
    *) echo "Usage: state-machine {start|status}" ;;
esac
EOF

# 3. 设置执行权限
chmod +x ~/.openclaw-gsdv2/core/state-machine.sh
```

### **第二步：启动GSD V2状态机**

```bash
# 1. 启动状态机（后台运行）
nohup ~/.openclaw-gsdv2/core/state-machine.sh start > ~/.openclaw-gsdv2/logs/state-machine.log 2>&1 &

# 2. 验证启动状态
ps aux | grep state-machine | grep -v grep

# 3. 检查日志
tail -f ~/.openclaw-gsdv2/logs/state-machine.log
```

### **第三步：适配队列配置到GSD V2**

```bash
# 1. 备份原队列配置
cp /Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json ~/.openclaw-gsdv2/backups/

# 2. 更新队列路由配置（将opencode_build改为claude-executor）
sed -i '' 's/"opencode_build"/"claude-executor"/g' /Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json

# 3. 验证配置更新
grep -n "runner_mode" /Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json
```

## 📊 **每日7点监控报告机制**

### **创建每日报告脚本**

```bash
# 创建每日报告脚本
cat > ~/.openclaw-gsdv2/scripts/daily-report.sh << 'EOF'
#!/bin/bash
# GSD V2 每日7点智能工作流报告

REPORT_FILE="$HOME/.openclaw-gsdv2/logs/daily-reports/report-$(date +%Y%m%d).md"
mkdir -p "$(dirname "$REPORT_FILE")"

# 报告头
cat > "$REPORT_FILE" << HEADER
# GSD V2 智能工作流日报 - $(date)

**报告时间**: $(date)
**监控目标**: Athena-Open Human 智能工作流稳定性

## 📊 系统状态概览
HEADER

# 检查GSD V2状态机运行状态
if ps aux | grep -q "state-machine.sh start" | grep -v grep; then
    echo "- ✅ **GSD V2状态机**: 运行中" >> "$REPORT_FILE"
else
    echo "- ❌ **GSD V2状态机**: 未运行" >> "$REPORT_FILE"
fi

# 检查队列配置
if [ -f "$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json" ]; then
    echo "- ✅ **队列配置**: 存在" >> "$REPORT_FILE"
else
    echo "- ❌ **队列配置**: 缺失" >> "$REPORT_FILE"
fi

# 检查EVO文件夹状态
evo_count=$(find "$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/013-EVO" -name "*.md" -mtime -1 2>/dev/null | wc -l)
echo "- 📋 **新EVO文件**: $evo_count 个" >> "$REPORT_FILE"

# 检查AI-plan执行状态
aiplan_count=$(find "$HOME/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan" -name "*.queue.json" 2>/dev/null | wc -l)
echo "- 🎯 **活跃队列**: $aiplan_count 个" >> "$REPORT_FILE"

# 添加建议部分
cat >> "$REPORT_FILE" << FOOTER

## 🚨 风险与建议

### 今日重点关注
1. **GSD V2状态机稳定性** - 确保持续运行
2. **队列执行成功率** - 监控任务完成情况
3. **EVO到AI-plan流转** - 保障智能工作流畅通

### 执行建议
- 如状态机未运行，立即执行重启指令
- 检查队列配置是否正确适配GSD V2
- 验证Claude Code CLI执行质量

## 📈 性能指标
- **系统可用性**: 待监控数据
- **任务执行率**: 待监控数据
- **错误处理**: 待监控数据

---
**报告生成时间**: $(date)
**下次报告**: 明日7:00
FOOTER

echo "📊 日报已生成: $REPORT_FILE"
EOF

chmod +x ~/.openclaw-gsdv2/scripts/daily-report.sh
```

### **设置每日7点定时任务**

```bash
# 1. 创建cron任务（每日7点执行）
(crontab -l 2>/dev/null; echo "0 7 * * * $HOME/.openclaw-gsdv2/scripts/daily-report.sh") | crontab -

# 2. 验证cron任务
crontab -l | grep daily-report

# 3. 立即测试报告生成
$HOME/.openclaw-gsdv2/scripts/daily-report.sh
```

## 🔧 **故障恢复指令**

### **状态机重启指令**

```bash
# 1. 停止现有状态机
pkill -f "state-machine.sh start"

# 2. 清理残留进程
sleep 2
pkill -9 -f "state-machine.sh start" 2>/dev/null || true

# 3. 重新启动
nohup ~/.openclaw-gsdv2/core/state-machine.sh start > ~/.openclaw-gsdv2/logs/state-machine.log 2>&1 &

# 4. 验证启动
ps aux | grep state-machine | grep -v grep
```

### **队列配置恢复指令**

```bash
# 1. 恢复队列配置（如配置出错）
cp ~/.openclaw-gsdv2/backups/.athena-auto-queue.json /Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/

# 2. 重新适配GSD V2
sed -i '' 's/"opencode_build"/"claude-executor"/g' /Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json
```

## 📋 **执行检查清单**

### **立即执行项目**
- [ ] 创建GSD V2目录结构
- [ ] 部署状态机引擎
- [ ] 启动状态机监控
- [ ] 适配队列配置
- [ ] 设置每日报告机制

### **每日监控项目**
- [ ] GSD V2状态机运行状态
- [ ] 队列配置正确性
- [ ] EVO文件夹变化监控
- [ ] AI-plan执行状态
- [ ] 系统稳定性指标

## 🎯 **成功指标**

### **技术指标**
- ✅ **GSD V2状态机**: 持续运行无中断
- ✅ **队列适配**: 正确路由到Claude Code CLI
- ✅ **监控覆盖**: 全链路状态监控

### **业务指标**
- ✅ **EVO流转**: 新想法及时进入执行流程
- ✅ **AI-plan执行**: 任务按时完成
- ✅ **系统稳定性**: 智能工作流持续畅通

---

**执行状态**: 指令就绪，可立即执行  
**监控机制**: 每日7点自动报告  
**保障目标**: Athena-Open Human智能工作流稳定运行