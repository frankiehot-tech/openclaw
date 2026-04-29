# 🚀 Athena/Open Human 基因管理队列快速启动指南

**版本**: 1.0
**生成时间**: 2026-04-05
**执行状态**: 准备就绪

---

## ⚡ 快速启动（3 步完成）

### 步骤 1: 验证队列运行器

```bash
# 检查队列运行器是否正在运行
ps aux | grep athena_ai_plan_runner | grep -v grep

# 如果未运行，启动它
python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py
```

### 步骤 2: 启动监控

```bash
# 启动监控脚本
python3 /Volumes/1TB-M2/openclaw/scripts/monitor_gene_management.py
```

### 步骤 3: 访问 Web 界面

```bash
# 在浏览器中打开
open http://127.0.0.1:8080
```

---

## 📋 完整执行清单

### 立即执行 ✅

- [x] 1. 查看操作指南 (`scripts/gene_management_queue_setup_guide.md`)
- [x] 2. 创建队列配置文件
  - [x] `scripts/gene_management_config.json`
  - [x] `scripts/gene_management_queue_manifest.json`
  - [x] `scripts/gene_management_queue_setup_guide.md`
- [x] 3. 创建执行指令文档
  - [x] `OpenHuman-Athena-OpenHuman 基因管理 Agent 工程实施方案-VSCode 执行指令.md`
- [x] 4. 创建监控脚本
  - [x] `scripts/monitor_gene_management.py`
- [ ] 5. 手动复制队列文件到 AI Plan 目录
- [ ] 6. 启动队列运行器
- [ ] 7. 启动监控脚本

### 监控和优化 🔄

- [ ] 4. 监控任务执行进度
  - [ ] 查看 Web 界面
  - [ ] 查看监控脚本输出
  - [ ] 检查日志文件
- [ ] 5. 验证各阶段实施效果
  - [ ] G0 阶段验证
  - [ ] G1 阶段验证
  - [ ] G2 阶段验证
  - [ ] Audit 阶段验证
- [ ] 6. 根据实际情况调整后续实施策略
  - [ ] 评估执行时间
  - [ ] 分析瓶颈问题
  - [ ] 调整资源配置

---

## 🎯 任务执行时间线

```
时间轴 (预计):

12:55 ─┬─ 队列设置完成 ✅
       │
12:56 ─┼─ G0 阶段开始执行 (基础设施搭建)
       │   预计耗时：30 分钟
       │
13:26 ─┼─ G1 阶段开始执行 (CLI 命令实现)
       │   预计耗时：1 小时
       │
14:26 ─┼─ G2 阶段开始执行 (队列系统集成)
       │   预计耗时：45 分钟
       │
15:11 ─┼─ Audit 阶段开始执行 (实施审计)
       │   预计耗时：30 分钟
       │
15:41 ─┴─ 所有任务执行完成 🎉
          总耗时：2 小时 45 分钟
```

---

## 📊 实时监控命令

### 队列状态监控

```bash
# 查看当前任务
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json | jq '.current_item_id'

# 查看任务计数
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json | jq '.counts'

# 持续监控 (每 5 秒刷新)
watch -n 5 'cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json | jq ".counts"'
```

### 日志监控

```bash
# 查看最新日志
tail -f /Volumes/1TB-M2/openclaw/logs/athena_ai_plan_runner.log

# 查看监控日志
tail -f /Volumes/1TB-M2/openclaw/logs/gene_management_monitor.log

# 搜索特定任务日志
grep "gene_mgmt" /Volumes/1TB-M2/openclaw/logs/athena_ai_plan_runner.log
```

### 进度验证

```bash
# 运行验证脚本
python3 /Volumes/1TB-M2/openclaw/scripts/verify_gene_management.py

# 查看执行报告
cat /Volumes/1TB-M2/openclaw/gene_management_execution_status.md
```

---

## 🔍 故障排查

### 问题 1: 队列未启动

**症状**: 队列状态一直为 `pending`

**解决方案**:
```bash
# 1. 检查队列运行器
ps aux | grep athena_ai_plan_runner

# 2. 重启队列运行器
killall athena_ai_plan_runner.py
python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py

# 3. 检查队列文件
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json
```

### 问题 2: 任务执行失败

**症状**: 任务状态变为 `failed`

**解决方案**:
```bash
# 1. 查看失败原因
grep "failed" /Volumes/1TB-M2/openclaw/logs/athena_ai_plan_runner.log

# 2. 查看错误详情
cat /Volumes/1TB-M2/openclaw/logs/athena_ai_plan_runner.log | tail -100

# 3. 重试失败任务
python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py --retry-failed
```

### 问题 3: 队列卡住

**症状**: 任务长时间处于 `running` 状态

**解决方案**:
```bash
# 1. 检查超时情况
# 查看监控脚本输出的超时警告

# 2. 手动终止卡住的任务
# 通过 Web 界面或命令行终止

# 3. 恢复队列执行
python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py --resume
```

---

## 📈 成功标准检查

### G0 阶段 (基础设施)

- [ ] EVO 目录结构创建完成
- [ ] EVO_GENOME.md 文件创建
- [ ] .evo/config.yaml 配置文件创建
- [ ] G0 基因模板内容正确

### G1 阶段 (CLI 实现)

- [ ] scripts/evo_cli.py 创建完成
- [ ] 基础命令可执行 (scan, review, status, genome-show)
- [ ] CLI 帮助信息显示正常
- [ ] 命令输出符合预期

### G2 阶段 (队列集成)

- [ ] 队列清单文件创建
- [ ] 队列状态文件配置正确
- [ ] Web 界面显示基因管理队列
- [ ] 任务自动执行正常

### Audit 阶段 (审计)

- [ ] 审计报告生成
- [ ] 所有验证测试通过
- [ ] 性能指标符合预期
- [ ] 系统稳定性验证通过

---

## 💡 优化建议

### 性能优化

1. **并发控制**: 确保 WIP=1，避免多任务并发
2. **资源监控**: 监控系统内存和 CPU 使用
3. **超时设置**: 根据实际执行情况调整超时时间

### 质量保障

1. **阶段验证**: 每个阶段完成后立即验证
2. **日志记录**: 保留完整的执行日志
3. **回滚机制**: 准备好回滚方案

### 效率提升

1. **自动化监控**: 使用监控脚本自动跟踪进度
2. **实时告警**: 异常情况及时通知
3. **经验总结**: 每阶段结束后总结经验

---

## 📞 获取帮助

### 文档资源

- **操作指南**: `scripts/gene_management_queue_setup_guide.md`
- **执行状态**: `gene_management_execution_status.md`
- **任务配置**: `scripts/gene_management_config.json`

### 支持渠道

- **技术文档**: 查看相关 Markdown 文档
- **日志文件**: `/Volumes/1TB-M2/openclaw/logs/`
- **监控输出**: 运行中的监控脚本

---

## 🎉 预期成果

执行完成后，你将获得:

1. ✅ **完整的基因序列基础设施** - EVO 目录结构和配置文件
2. ✅ **可操作的 CLI 界面** - evo 系列命令完整实现
3. ✅ **深度集成的队列系统** - 与 AI Plan 系统无缝对接
4. ✅ **全面的审计报告** - 实施效果验证和总结

**基因管理系统将准备就绪，可以开始实际的基因递归演进操作！**

---

**最后更新**: 2026-04-05 12:55:00
**状态**: 准备执行