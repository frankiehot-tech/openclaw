# OpenClaw 工具参考指南

## 📋 工具分类概览

OpenClaw项目包含超过245个脚本工具，按功能分为以下7个核心类别：

| 类别 | 工具数量 | 主要功能 | 关键脚本示例 |
|------|----------|----------|--------------|
| **核心引擎** | ~15 | 系统核心功能和工作流引擎 | `athena_ai_plan_runner.py`, `athena_web_desktop_compat.py` |
| **队列管理** | ~40 | 队列操作、任务编排和状态管理 | `queue_liveness_probe.py`, `add_task_to_queue.py` |
| **监控告警** | ~25 | 系统监控、健康检查和告警通知 | `queue_monitor.py`, `queue_monitor_dashboard.py` |
| **文档工具** | ~30 | 文档生成、管理和迁移工具 | `automate_document_migration.py`, `validate_path_config.py` |
| **审计分析** | ~50 | 系统审计、性能分析和问题诊断 | `athena_queue_deep_audit.py`, `analyze_dependencies.py` |
| **系统维护** | ~35 | 环境配置、备份恢复和清理工具 | `setup_environment.py`, `cleanup_migrated_files.py` |
| **测试工具** | ~50 | 功能测试、压力测试和验证工具 | `stress_test_athena_queue.py`, `fault_injection_test_fixed.py` |

## 🧠 核心引擎工具

### Athena队列运行器
**主要脚本**: `athena_ai_plan_runner.py`
**功能**: 智能任务编排的核心引擎，基于契约框架执行任务
```bash
# 启动队列运行器
python3 scripts/athena_ai_plan_runner.py --queue ~/.openclaw/plan_queue/<队列文件>.json

# 查看帮助
python3 scripts/athena_ai_plan_runner.py --help

# 调试模式
python3 scripts/athena_ai_plan_runner.py --queue <队列文件> --verbose --debug
```

### Athena Web桌面兼容层
**主要脚本**: `athena_web_desktop_compat.py`
**功能**: 提供Web界面与队列系统的API兼容层
```bash
# 启动Web服务
python3 scripts/athena_web_desktop_compat.py --port 5001

# 作为守护进程运行
nohup python3 scripts/athena_web_desktop_compat.py > web_server.log 2>&1 &
```

### 智能工作流引擎
**相关脚本**: `smart_orchestrator.py`, `workflow_engine.py`
**功能**: 智能路由决策和契约框架执行

## 🔄 队列管理工具

### 队列监控探针
**主要脚本**: `queue_liveness_probe.py`
**功能**: 检测队列运行器心跳，确保系统活跃
```bash
# 检查队列运行器状态
python3 scripts/queue_liveness_probe.py --pid-file ~/.openclaw/athena_ai_plan_runner.pid

# 自动重启失效的运行器
python3 scripts/queue_liveness_probe.py --auto-restart --check-interval 60
```

### 任务管理工具
**关键脚本**:
- `add_task_to_queue.py` - 添加新任务到队列
- `manual_launch_task.py` - 手动拉起任务
- `retry_failed_tasks.py` - 重试失败任务
- `pause_queue.py` - 暂停队列执行
- `resume_queue.py` - 恢复队列执行

```bash
# 添加任务到队列
python3 scripts/add_task_to_queue.py --queue openhuman_aiplan_build_priority.json --task new_task.json

# 手动拉起任务
python3 scripts/manual_launch_task.py --item-id task_123 --route-id gene_mgmt_audit

# 重试所有失败任务
python3 scripts/retry_failed_tasks.py --queue openhuman_aiplan_build_priority.json --all
```

### 队列状态检查
**关键脚本**: `check_queue_status.py`, `analyze_queue_thoroughly.py`
```bash
# 检查队列详细状态
python3 scripts/check_queue_status.py --queue ~/.openclaw/plan_queue/openhuman_aiplan_build_priority.json

# 全面分析队列
python3 scripts/analyze_queue_thoroughly.py --queue-file <队列文件> --output report.json
```

## 📊 监控告警工具

### 队列监控系统
**主要脚本**: `queue_monitor.py`
**功能**: 实时监控队列健康度，支持多种告警渠道
```bash
# 启动队列监控
python3 scripts/queue_monitor.py --config queue_monitor_config.yaml

# 只检查不持续监控
python3 scripts/queue_monitor.py --check-once --verbose

# 健康检查模式
python3 scripts/queue_monitor.py --health-check
```

### 监控仪表板
**主要脚本**: `queue_monitor_dashboard.py`
**功能**: Web界面展示系统监控数据
```bash
# 启动监控仪表板
python3 scripts/queue_monitor_dashboard.py --port 5002

# 访问仪表板
# 浏览器打开: http://localhost:5002
```

### 告警配置
**配置文件**: `queue_monitor_config.yaml`
```yaml
# 告警配置示例
monitoring:
  interval: 300  # 检查间隔（秒）
  alert_thresholds:
    queue_stalled_minutes: 30
    queue_failed_tasks: 5
  
  notifications:
    email:
      enabled: false
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "your-email@gmail.com"
      password: "your-app-password"
      recipients: ["team@example.com"]
    
    slack:
      enabled: false
      webhook_url: "https://hooks.slack.com/services/..."
      channel: "#alerts"
```

## 📚 文档工具

### 文档迁移工具
**主要脚本**: `automate_document_migration.py`
**功能**: 自动化迁移文档到三才六层架构
```bash
# 批量迁移文档
python3 scripts/automate_document_migration.py --source . --target docs/ --dry-run

# 实际执行迁移
python3 scripts/automate_document_migration.py --execute --report migration_report.md
```

### 路径验证工具
**主要脚本**: `validate_path_config.py`
**功能**: 验证环境配置和路径完整性
```bash
# 验证所有路径配置
python3 validate_path_config.py

# 详细模式
python3 validate_path_config.py --verbose

# 修复路径问题
python3 validate_path_config.py --repair
```

### 文档质量工具
**关键脚本**:
- `check_document_links.py` - 检查文档链接有效性
- `validate_document_format.py` - 验证文档格式规范
- `generate_document_stats.py` - 生成文档统计报告

```bash
# 检查所有文档链接
python3 scripts/check_document_links.py --directory docs/

# 验证特定文档格式
python3 scripts/validate_document_format.py --file docs/user/user-guide.md

# 生成文档统计
python3 scripts/generate_document_stats.py --output stats.json
```

## 🔍 审计分析工具

### 深度队列审计
**主要脚本**: `athena_queue_deep_audit.py`
**功能**: 深度分析队列系统问题和性能瓶颈
```bash
# 执行深度审计
python3 scripts/athena_queue_deep_audit.py --queue-file <队列文件> --output audit_report.md

# 包含建议修复方案
python3 scripts/athena_queue_deep_audit.py --with-fixes --export-json audit_data.json
```

### 依赖分析工具
**主要脚本**: `analyze_dependencies.py`
**功能**: 分析任务依赖关系和执行顺序
```bash
# 分析队列依赖
python3 scripts/analyze_dependencies.py --queue-file <队列文件> --visualize

# 检测循环依赖
python3 scripts/analyze_dependencies.py --detect-cycles --output cycles_report.md
```

### 性能分析工具
**关键脚本**:
- `analyze_queue_performance.py` - 分析队列性能指标
- `monitor_system_resources.py` - 监控系统资源使用
- `generate_performance_report.py` - 生成性能报告

```bash
# 分析队列性能
python3 scripts/analyze_queue_performance.py --queue <队列文件> --duration 3600

# 监控系统资源
python3 scripts/monitor_system_resources.py --duration 300 --interval 10

# 生成HTML性能报告
python3 scripts/generate_performance_report.py --output performance_report.html
```

## 🛠️ 系统维护工具

### 环境配置工具
**主要脚本**: `setup_environment.py`
**功能**: 一键配置OpenClaw开发环境
```bash
# 初始化环境配置
python3 setup_environment.py --init

# 重置环境配置
python3 setup_environment.py --reset --confirm

# 验证环境完整性
python3 setup_environment.py --validate
```

### 备份恢复工具
**关键脚本**:
- `archive_completed_queues.py` - 归档已完成队列
- `backup_system_state.py` - 备份系统状态
- `restore_from_backup.py` - 从备份恢复

```bash
# 归档已完成队列
python3 scripts/archive_completed_queues.py --days-old 7 --destination ~/.openclaw/archived_queues/

# 创建系统状态备份
python3 scripts/backup_system_state.py --backup-dir ~/.openclaw/backups/ --include-queues --include-config
```

### 清理维护工具
**主要脚本**: `cleanup_migrated_files.py`
**功能**: 安全清理已迁移文件，支持回收站机制
```bash
# 模拟清理（预览效果）
python3 scripts/cleanup_migrated_files.py --simulate --report cleanup_preview.md

# 实际执行清理
python3 scripts/cleanup_migrated_files.py --execute

# 恢复清理的文件
mv .document_recycle_bin/原文件路径 .
```

## 🧪 测试工具

### 压力测试工具
**主要脚本**: `stress_test_athena_queue.py`
**功能**: 压力测试队列系统性能和稳定性
```bash
# 执行压力测试
python3 scripts/stress_test_athena_queue.py --tasks-per-minute 50 --duration 300

# 生成测试报告
python3 scripts/stress_test_athena_queue.py --tasks-per-minute 100 --duration 600 --output stress_test_report.md
```

### 故障注入测试
**主要脚本**: `fault_injection_test_fixed.py`
**功能**: 注入故障测试系统恢复能力
```bash
# 运行故障注入测试
python3 scripts/fault_injection_test_fixed.py --tests all --output fault_test_results.json

# 特定故障类型测试
python3 scripts/fault_injection_test_fixed.py --test-type process_crash --iterations 5
```

### 集成测试工具
**关键脚本**:
- `integration_test_suite.py` - 集成测试套件
- `contract_framework_test.py` - 契约框架测试
- `smart_orchestrator_test.py` - 智能路由测试

```bash
# 运行完整集成测试
python3 scripts/integration_test_suite.py --test-all --verbose

# 测试契约框架
python3 scripts/contract_framework_test.py --contracts all --output test_results.md
```

## 🔧 工具使用最佳实践

### 1. 环境配置检查
```bash
# 每次使用前检查环境
python3 validate_path_config.py

# 验证脚本依赖
python3 scripts/check_script_dependencies.py
```

### 2. 工具版本管理
```bash
# 记录工具版本
python3 scripts/record_tool_versions.py --output tool_versions.json

# 检查工具更新
python3 scripts/check_for_updates.py --tool-scripts scripts/
```

### 3. 安全操作原则
- **备份优先**: 重要操作前先备份
- **预览模式**: 使用`--dry-run`或`--simulate`预览效果
- **回收站机制**: 使用清理工具的回收站功能
- **权限检查**: 检查脚本执行权限和文件访问权限

### 4. 监控集成
```bash
# 将工具执行集成到监控系统
python3 scripts/integrate_tool_with_monitoring.py --tool <工具名> --monitoring-config queue_monitor_config.yaml
```

## 🚨 常见问题解决

### 工具无法执行
```bash
# 检查Python版本
python3 --version

# 检查依赖安装
pip install -r scripts/requirements.txt

# 检查脚本权限
chmod +x scripts/*.py
```

### 环境变量问题
```bash
# 检查环境变量
echo $OPENCLAW_ROOT
echo $ATHENA_RUNTIME_ROOT

# 重新加载配置
source ~/.zshrc
# 或直接设置
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"
```

### 路径配置错误
```bash
# 检查paths.py配置
cat config/paths.py

# 重新生成路径配置
python3 setup_environment.py --reset
```

## 📖 相关资源

### 文档参考
- [快速开始指南](user/getting-started.md) - 新手入门指南
- [完整用户指南](user/user-guide.md) - 详细功能说明
- [Claude Code配置指南](user/claude-code-config.md) - Claude Code集成配置

### 技术支持
- **问题反馈**: 在项目issue页面提交问题
- **功能建议**: 提交功能请求issue
- **贡献指南**: 查看`docs/user/contributing.md`

### 工具开发
- **工具模板**: `templates/tool_template.py`
- **测试框架**: `templates/test_template.py`
- **文档生成**: `templates/documentation_template.md`

---

**最后更新**: 2026-04-19  
**版本**: 1.0  
**维护者**: OpenClaw工具文档团队  
**文档状态**: 活跃维护中  

> **提示**: 本工具参考指南将持续更新。建议定期查看`docs/user/`目录获取最新版本。如有新工具添加或现有工具更新，请及时更新此文档。