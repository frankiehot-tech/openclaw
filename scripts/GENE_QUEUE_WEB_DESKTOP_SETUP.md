# 🧬 基因管理队列 Web Desktop 显示配置指南

**生成时间**: 2026-04-05 13:35
**问题**: 基因管理队列未在 Athena Web Desktop 中显示
**状态**: 需要手动配置

---

## 🔍 问题分析

基因管理队列文件已创建：
- ✅ 队列状态文件：`.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json`
- ✅ 队列清单文件：`scripts/gene_management_queue_manifest.json`
- ❌ 但未在 Web Desktop 界面显示

**原因**: 
1. 自动队列配置文件位于受保护的 Documents 目录
2. Web Desktop 需要手动刷新或重启才能发现新队列
3. 可能需要更新队列路由配置

---

## 🔧 解决方案（3 选 1）

### 方案 1: 刷新 Web Desktop（推荐 ⭐⭐⭐⭐⭐）

**最简单的方法** - 强制刷新浏览器缓存：

```bash
# 1. 在浏览器中访问
http://127.0.0.1:8080

# 2. 强制刷新
# macOS: Cmd + Shift + R
# Windows: Ctrl + Shift + R

# 3. 清除浏览器缓存（可选）
# Chrome: 设置 > 隐私和安全 > 清除浏览数据
# Safari: 开发 > 清空缓存
```

**预期效果**: Web Desktop 应该自动发现新队列并显示

---

### 方案 2: 重启 Web Desktop 服务

如果刷新无效，重启 Web 服务：

```bash
# 1. 查找当前 Web 服务进程
ps aux | grep -E "(web_desktop|athena_web)" | grep -v grep

# 2. 停止 Web 服务
# 找到进程 PID 后执行
kill <PID>

# 3. 重新启动 Web 服务
python3 /Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py

# 4. 重新访问
http://127.0.0.1:8080
```

**预期效果**: 服务重启后会重新加载所有队列配置

---

### 方案 3: 手动更新队列路由配置

如果上述方法都无效，手动添加队列路由：

#### 步骤 1: 创建队列路由配置文件

```bash
# 创建队列路由配置
cat > /Volumes/1TB-M2/openclaw/.openclaw/gene_management_route.json << 'EOF'
{
  "route_id": "aiplan_gene_management",
  "queue_id": "openhuman_aiplan_gene_management_20260405",
  "name": "OpenHuman AIPlan 基因管理队列",
  "description": "基因管理系统实施的专用队列",
  "manifest_path": "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json",
  "state_path": "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json",
  "runner_mode": "opencode_build",
  "priority": "S0",
  "enabled": true,
  "display_order": 1,
  "defaults": {
    "entry_stage": "build",
    "risk_level": "low",
    "unattended_allowed": true
  },
  "created_at": "2026-04-05T13:35:00"
}
EOF
```

#### 步骤 2: 更新 Web Desktop 配置

编辑 Web Desktop 配置文件（如果存在）：

```bash
# 检查配置文件位置
ls -la /Volumes/1TB-M2/openclaw/mini-agent/config/ | grep -i web
ls -la /Volumes/1TB-M2/openclaw/workspace/ | grep -i web
ls -la /Volumes/1TB-M2/openclaw/.openclaw/ | grep -i web

# 如果找到配置文件，添加基因管理队列
# 在 queues 数组中添加:
{
  "queue_id": "openhuman_aiplan_gene_management_20260405",
  "name": "基因管理队列",
  "display_order": 1,
  "enabled": true
}
```

#### 步骤 3: 重启并验证

```bash
# 重启 Web Desktop 服务（参考方案 2）
# 访问 Web 界面验证
http://127.0.0.1:8080
```

---

## 📊 验证队列显示

### 验证步骤

1. **访问 Web Desktop**
   ```
   http://127.0.0.1:8080
   ```

2. **检查队列列表**
   
   应该看到以下队列：
   - ✅ OpenHuman AIPlan 优先执行队列
   - ✅ OpenHuman AIPlan Codex 审计队列
   - ✅ OpenHuman AIPlan 自动策划队列
   - 🆕 **OpenHuman AIPlan 基因管理队列** ← 新增

3. **检查队列状态**
   
   基因管理队列应显示：
   ```
   运行中：1
   待执行：3
   手动：0
   失败：0
   已完成：0
   ```

4. **查看任务列表**
   
   点击基因管理队列，应看到 4 个任务：
   - gene_mgmt_g0_infrastructure (running)
   - gene_mgmt_g1_cli_implementation (pending)
   - gene_mgmt_g2_queue_integration (pending)
   - gene_mgmt_audit (pending)

---

## 🚀 快速验证命令

```bash
# 1. 检查队列文件是否存在
ls -la /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json

# 2. 查看队列状态
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json | jq '.queue_status, .current_item_id, .counts'

# 3. 检查 Web 服务是否运行
ps aux | grep -E "8080|web_desktop" | grep -v grep

# 4. 测试 Web 服务响应
curl -s http://127.0.0.1:8080 | head -20

# 5. 如果可能，检查 API 返回的队列数据
curl -s http://127.0.0.1:8080/api/queues 2>/dev/null | jq '.routes[] | select(.queue_id | contains("gene"))' || echo "未找到基因管理队列"
```

---

## 💡 常见问题

### Q1: 刷新后仍然不显示

**A**: 尝试以下操作：
1. 清除浏览器所有缓存和 Cookie
2. 使用隐私/无痕模式访问
3. 换一个浏览器尝试
4. 重启 Web Desktop 服务

### Q2: 显示队列但没有任务

**A**: 检查队列状态文件：
```bash
# 查看队列状态
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json | jq '.items | keys'

# 如果 items 为空，需要重新创建队列
python3 /Volumes/1TB-M2/openclaw/scripts/gene_management_queue_setup.py
```

### Q3: 显示"手动保留"状态

**A**: 这是正常状态，需要手动拉起任务：
1. 在 Web 界面点击"拉起失败任务"或"运行选中任务"
2. 或者通过命令行启动队列运行器

### Q4: 队列显示但状态不正确

**A**: 检查队列运行器是否运行：
```bash
# 检查运行器进程
ps aux | grep athena_ai_plan_runner | grep -v grep

# 如果未运行，启动它
python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py
```

---

## 📝 配置检查清单

执行以下检查，确保配置正确：

- [ ] **队列状态文件存在**
  - 路径：`.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json`
  - 内容：包含 4 个任务项

- [ ] **队列清单文件存在**
  - 路径：`scripts/gene_management_queue_manifest.json`
  - 内容：完整的队列配置

- [ ] **Web Desktop 服务运行中**
  - 进程：`athena_web_desktop_compat.py`
  - 端口：8080

- [ ] **队列运行器运行中**
  - 进程：`athena_ai_plan_runner.py`
  - 状态：正常运行

- [ ] **浏览器缓存已清除**
  - 操作：强制刷新 (Cmd+Shift+R)
  - 验证：查看页面源代码确认加载最新资源

---

## 🎯 预期结果

配置完成后，Athena Web Desktop 应显示：

### 任务队列区域

```
✨ 新增队列 ✨
┌────────────────────────────────────────┐
│ OpenHuman AIPlan 基因管理队列           │
│ 自动执行                                │
│                                         │
│ 运行中 1 · 待执行 3 · 手动 0 · 失败 0  │
│                                         │
│ 任务列表:                               │
│ 🔄 G0: 基础设施搭建 (running)           │
│ ⏳ G1: CLI 命令实现 (pending)           │
│ ⏳ G2: 队列集成 (pending)               │
│ ⏳ Audit: 实施审计 (pending)            │
└────────────────────────────────────────┘
```

### 任务详情

点击任一任务可查看：
- 任务标题
- 执行指令文档链接
- 预估时长
- 依赖关系
- 执行日志

---

## 🔗 相关文档

- **操作指南**: `scripts/gene_management_queue_setup_guide.md`
- **快速启动**: `scripts/QUICKSTART_GENE_MANAGEMENT.md`
- **执行状态**: `gene_management_execution_status.md`
- **执行总结**: `gene_management_execution_summary.md`

---

## 📞 获取帮助

如果以上方法都无效：

1. **检查日志文件**
   ```bash
   tail -f /Volumes/1TB-M2/openclaw/logs/athena_web_desktop.log
   tail -f /Volumes/1TB-M2/openclaw/logs/athena_ai_plan_runner.log
   ```

2. **查看浏览器控制台**
   - 按 F12 打开开发者工具
   - 查看 Console 标签页的错误信息
   - 查看 Network 标签页的 API 请求

3. **手动验证配置**
   ```bash
   # 验证所有配置文件
   python3 /Volumes/1TB-M2/openclaw/scripts/verify_gene_management.py
   ```

---

**最后更新**: 2026-04-05 13:35
**状态**: 等待 Web Desktop 显示基因管理队列
