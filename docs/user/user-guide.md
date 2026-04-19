# OpenClaw 完整用户指南

## 📖 指南概述

OpenClaw是一个基于MAREF（多智能体递归进化框架）的工程化AI开发平台，专注于智能工作流管理和多智能体协作。本指南详细介绍所有功能和使用方法。

## 🏗️ 系统架构

### MAREF三才六层模型
OpenClaw采用三才六层架构组织系统：

| 层级 | 作用 | 对应目录 | 关键文档 |
|------|------|----------|----------|
| **战略层** | 定义核心认知框架和智能体角色 | `docs/architecture/` | 认知DNA、智能体架构 |
| **管理层** | 制定技术规范和接口标准 | `docs/technical/specifications/` | 接口定义、规范文档 |
| **流程层** | 定义运维流程和操作指南 | `docs/technical/operations/` | 运维手册、操作指南 |
| **应用层** | 实现具体功能和应用部署 | `docs/technical/deployment/` | 部署指南、配置说明 |
| **平台层** | 提供审计和分析能力 | `docs/audit/` | 审计报告、性能分析 |
| **环境层** | 支持用户交互和使用 | `docs/user/` | 用户指南、快速开始 |

### 核心组件
1. **Athena队列系统** - 智能任务编排引擎
2. **SmartOrchestrator** - 智能工作流路由决策
3. **契约框架** - 确保系统一致性的约束体系
4. **文档管理系统** - 三才六层文档架构
5. **监控告警系统** - 实时系统健康度监控

## 🚀 快速开始

### 首次使用步骤
1. **环境配置**：设置`OPENCLAW_ROOT`和`ATHENA_RUNTIME_ROOT`环境变量
2. **路径验证**：运行`python3 validate_path_config.py`验证配置
3. **文档导航**：查看`docs/README.md`了解文档结构
4. **队列启动**：启动Athena队列监控和运行器

详细步骤参见：[快速开始指南](user/getting-started.md)

## 🧠 Athena队列系统

### 队列管理

#### 查看队列状态
```bash
# 列出所有队列文件
ls -la ~/.openclaw/plan_queue/

# 查看特定队列状态
python3 scripts/check_queue_status.py --queue ~/.openclaw/plan_queue/openhuman_aiplan_build_priority.json

# 监控队列运行器
tail -f ~/.openclaw/queue_runner.log
```

#### 队列操作
```bash
# 启动队列运行器
cd scripts
python3 athena_ai_plan_runner.py --queue ~/.openclaw/plan_queue/<队列文件>.json

# 停止队列运行器
kill -TERM $(cat ~/.openclaw/athena_ai_plan_runner.pid)

# 重启队列运行器
./scripts/restart_queue_runner.sh
```

#### 任务管理
```bash
# 添加新任务到队列
python3 scripts/add_task_to_queue.py --queue <队列文件> --task <任务JSON>

# 手动拉起失败任务
python3 scripts/manual_launch_task.py --item-id <任务ID> --route-id <路由ID>

# 重试失败任务
python3 scripts/retry_failed_tasks.py --queue <队列文件>
```

### 智能工作流

#### SmartOrchestrator路由
SmartOrchestrator根据多个维度智能路由任务：

| 决策维度 | 说明 | 影响 |
|----------|------|------|
| **基础路由** | 任务类型到执行器的映射 | 确保正确性 |
| **适应性调整** | 系统负载和资源状况 | 优化性能 |
| **成本优化** | API成本和预算控制 | 控制成本 |
| **风险评估** | 任务失败风险预测 | 提高可靠性 |

#### 执行器类型
OpenClaw定义了10种执行器类型：

| 执行器 | 内部阶段 | 适用场景 |
|--------|----------|----------|
| **athena_thinker** | think | 复杂思考和分析任务 |
| **athena_planner** | plan | 项目规划和方案设计 |
| **opencode_build** | build | 代码编写和重构 |
| **codex_review** | review | 代码审查和质量检查 |
| **opencli_qa** | qa | 质量保证和测试 |
| **opencli_browser** | browse | 网页浏览和研究 |
| **codenav_edit** | edit | 代码编辑和优化 |
| **athena_search** | search | 信息搜索和检索 |
| **athena_research** | research | 深度研究和分析 |
| **manual_executor** | manual | 需要人工干预的任务 |

## 📚 文档系统

### 文档分类体系

#### 按三才六层分类
1. **架构文档** (`docs/architecture/`)
   - 系统设计文档
   - 智能体架构说明
   - 核心框架文档

2. **技术文档** (`docs/technical/`)
   - **specifications/** - 技术规范和接口定义
   - **operations/** - 运维指南和操作手册
   - **deployment/** - 部署指南和配置说明

3. **审计文档** (`docs/audit/YYYY-MM/`)
   - 按年月组织的审计报告
   - 性能分析文档
   - 问题跟踪记录

4. **用户文档** (`docs/user/`)
   - 用户指南和快速开始
   - 配置说明和工具参考
   - 最佳实践和案例研究

### 文档管理操作

#### 创建新文档
```bash
# 创建新的运维文档
cp docs/templates/operations-template.md docs/technical/operations/new-operation-guide.md

# 创建审计报告（自动按年月分类）
YEAR_MONTH=$(date +%Y-%m)
mkdir -p docs/audit/$YEAR_MONTH
echo "# 审计报告 - $(date)" > docs/audit/$YEAR_MONTH/new-audit-report.md
```

#### 文档搜索和导航
```bash
# 搜索特定内容
grep -r "Athena队列" docs/

# 查看文档索引
cat docs/README.md

# 查看特定分类文档
find docs/technical/operations -name "*.md" | head -20
```

#### 文档质量检查
```bash
# 检查文档链接有效性
python3 scripts/check_document_links.py

# 验证文档格式
python3 scripts/validate_document_format.py --file docs/user/user-guide.md

# 生成文档统计报告
python3 scripts/generate_document_stats.py
```

## 🔧 系统配置

### 环境配置

#### 核心环境变量
```bash
# OpenClaw项目根目录（必需）
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"

# Athena运行时根目录（通常与OPENCLAW_ROOT相同）
export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"

# 脚本路径（可选，方便访问）
export PATH="$OPENCLAW_ROOT/scripts:$PATH"
```

#### 持久化配置
```bash
# 添加到shell配置文件
echo 'export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"' >> ~/.zshrc
echo 'export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"' >> ~/.zshrc
echo 'export PATH="$OPENCLAW_ROOT/scripts:$PATH"' >> ~/.zshrc

# 立即生效
source ~/.zshrc
```

### 路径配置

#### 单一事实源原则
所有路径配置集中在`config/paths.py`：
```python
# config/paths.py 示例
import os

# 基础路径（从环境变量读取）
OPENCLAW_ROOT = os.environ.get('OPENCLAW_ROOT', '/Volumes/1TB-M2/openclaw')
ATHENA_RUNTIME_ROOT = os.environ.get('ATHENA_RUNTIME_ROOT', OPENCLAW_ROOT)

# 子目录路径（自动派生）
SCRIPTS_DIR = os.path.join(OPENCLAW_ROOT, 'scripts')
CONFIG_DIR = os.path.join(OPENCLAW_ROOT, 'config')
DOCS_DIR = os.path.join(OPENCLAW_ROOT, 'docs')
SKILLS_DIR = os.path.join(OPENCLAW_ROOT, 'skills')
```

#### 路径验证
```bash
# 验证所有路径配置
python3 validate_path_config.py

# 详细模式查看
python3 validate_path_config.py --verbose

# 修复路径问题
python3 validate_path_config.py --repair
```

### 监控配置

#### 队列监控配置
创建`queue_monitor_config.yaml`：
```yaml
# 队列监控配置示例
monitoring:
  interval: 300  # 检查间隔（秒）
  alert_thresholds:
    queue_stalled_minutes: 30
    queue_failed_tasks: 5
    queue_manual_hold_tasks: 3
  
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
    
    console:
      enabled: true
      level: "INFO"
    
    log:
      enabled: true
      file: "queue_monitor.log"
      level: "DEBUG"
```

#### 启动监控
```bash
# 启动队列监控
python3 scripts/queue_monitor.py --config queue_monitor_config.yaml

# 启动监控仪表板
python3 scripts/queue_monitor_dashboard.py

# 访问监控仪表板
# 浏览器打开: http://localhost:5002
```

## 🚨 故障排除

### 常见问题

#### 队列相关问题

**问题：队列停止运行**
```bash
# 检查队列运行器进程
ps aux | grep athena_ai_plan_runner.py

# 检查队列文件状态
ls -la ~/.openclaw/plan_queue/

# 重启队列运行器
cd scripts
python3 athena_ai_plan_runner.py --queue ~/.openclaw/plan_queue/<队列文件>.json
```

**问题：任务卡在pending状态**
```bash
# 检查队列状态
python3 scripts/check_queue_status.py --queue <队列文件>

# 检查任务依赖
python3 scripts/check_task_dependencies.py --task-id <任务ID>

# 手动触发任务执行
python3 scripts/manual_launch_task.py --item-id <任务ID> --route-id <路由ID>
```

**问题：Web界面显示异常**
```bash
# 检查Web服务器进程
ps aux | grep "python.*web_desktop"

# 检查Web服务日志
tail -f ~/.openclaw/web_server.log

# 重启Web服务
cd ~/.openclaw/core/
./restart_web_desktop.sh
```

#### 配置相关问题

**问题：环境变量不生效**
```bash
# 检查当前环境变量
echo $OPENCLAW_ROOT
echo $ATHENA_RUNTIME_ROOT

# 临时设置
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"
export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"

# 验证配置
python3 validate_path_config.py
```

**问题：路径配置错误**
```bash
# 检查paths.py配置
cat config/paths.py

# 重新生成路径配置
python3 setup_environment.py --reset

# 验证修复
python3 validate_path_config.py --repair --verbose
```

#### 文档相关问题

**问题：文档链接失效**
```bash
# 检查所有文档链接
python3 scripts/check_document_links.py

# 修复相对链接
python3 scripts/fix_document_links.py --directory docs/

# 更新文档索引
python3 scripts/update_document_index.py
```

### 诊断工具

#### 系统健康检查
```bash
# 运行完整健康检查
python3 scripts/system_health_check.py

# 检查特定组件
python3 scripts/system_health_check.py --component queue
python3 scripts/system_health_check.py --component web
python3 scripts/system_health_check.py --component docs
```

#### 性能诊断
```bash
# 监控系统资源使用
python3 scripts/monitor_system_resources.py --duration 300

# 分析队列性能
python3 scripts/analyze_queue_performance.py --queue <队列文件>

# 生成性能报告
python3 scripts/generate_performance_report.py --output performance_report.html
```

## 📈 高级功能

### 自定义智能体

#### 创建新智能体
1. **定义智能体能力**：在`skills/`目录创建技能定义
2. **集成到工作流**：更新`smart_orchestrator.py`中的路由规则
3. **测试验证**：运行智能体集成测试

#### 智能体技能开发
```python
# 技能定义示例 (skills/my_custom_skill.md)
# My Custom Skill

## 能力描述
- 处理特定类型任务
- 集成外部API
- 生成定制化输出

## 配置要求
- API密钥配置
- 环境变量设置
- 依赖库安装

## 使用示例
```bash
# 调用自定义技能
python3 scripts/execute_custom_skill.py --skill my_custom_skill --input <输入数据>
```

### 扩展契约框架

#### 自定义契约
```python
# 创建新契约
from workflow.contracts.base_contract import BaseContract

class CustomContract(BaseContract):
    """自定义契约示例"""
    
    def __init__(self):
        super().__init__(name="custom_contract", version="1.0")
    
    def validate(self, task_data):
        """验证任务数据"""
        # 实现自定义验证逻辑
        pass
    
    def apply(self, task_data):
        """应用契约规则"""
        # 实现自定义规则应用
        pass
```

#### 契约集成
```python
# 在智能工作流中集成新契约
from workflow.contracts.custom_contract import CustomContract

# 注册契约
SmartOrchestrator.register_contract(CustomContract())

# 在路由决策中使用
def route_with_custom_contract(task):
    if CustomContract().validate(task):
        return "custom_executor"
    return SmartOrchestrator.route_task(task)
```

### 监控告警扩展

#### 自定义告警规则
```yaml
# 扩展监控配置
custom_alerts:
  - name: "custom_metric_alert"
    condition: "custom_metric > threshold"
    threshold: 100
    severity: "WARNING"
    notification_channels: ["email", "slack"]
  
  - name: "business_rule_violation"
    condition: "business_metric < min_acceptable"
    min_acceptable: 0.95
    severity: "CRITICAL"
    notification_channels: ["email", "slack", "sms"]
```

#### 告警处理脚本
```python
# 自定义告警处理脚本
import yaml
from monitoring.alert_handler import AlertHandler

class CustomAlertHandler(AlertHandler):
    """自定义告警处理器"""
    
    def handle_alert(self, alert_data):
        """处理告警"""
        # 自定义告警处理逻辑
        if alert_data["severity"] == "CRITICAL":
            self.escalate_alert(alert_data)
        else:
            self.log_alert(alert_data)
```

## 🔄 工作流示例

### 典型使用场景

#### 场景1：新项目规划
```bash
# 1. 创建项目规划任务
python3 scripts/create_planning_task.py --project "新项目" --scope "完整实施方案"

# 2. 提交到规划队列
python3 scripts/add_task_to_queue.py --queue openhuman_aiplan_planning.json --task planning_task.json

# 3. 监控规划进度
python3 scripts/monitor_task_progress.py --task-id <规划任务ID>

# 4. 查看规划结果
cat ~/.openclaw/output/planning_results/<任务ID>/plan.md
```

#### 场景2：代码重构任务
```bash
# 1. 分析代码库
python3 scripts/analyze_codebase.py --directory /path/to/code --output analysis_report.json

# 2. 创建重构任务
python3 scripts/create_refactoring_task.py --analysis analysis_report.json --strategy "逐步重构"

# 3. 提交到构建队列
python3 scripts/add_task_to_queue.py --queue openhuman_aiplan_build_priority.json --task refactoring_task.json

# 4. 跟踪重构进度
python3 scripts/track_refactoring_progress.py --task-id <重构任务ID>
```

#### 场景3：系统审计
```bash
# 1. 启动系统审计
python3 scripts/start_system_audit.py --scope "全面审计" --duration "24小时"

# 2. 监控审计进度
python3 scripts/monitor_audit_progress.py --audit-id <审计ID>

# 3. 生成审计报告
python3 scripts/generate_audit_report.py --audit-id <审计ID> --format html

# 4. 查看审计结果
open ~/.openclaw/audit_reports/<审计ID>/audit_report.html
```

### 最佳实践

#### 队列管理最佳实践
1. **定期清理**：每周清理完成的队列文件
2. **容量规划**：监控队列长度，避免积压
3. **优先级设置**：合理设置任务优先级
4. **故障转移**：配置队列故障自动恢复

#### 文档管理最佳实践
1. **及时更新**：系统变更后立即更新文档
2. **版本控制**：重要文档使用版本号
3. **定期审计**：每月检查文档完整性和准确性
4. **知识沉淀**：将经验教训沉淀为文档

#### 监控告警最佳实践
1. **分层告警**：根据严重程度设置不同告警级别
2. **告警收敛**：避免告警风暴
3. **告警处理**：建立告警响应和处理流程
4. **持续优化**：定期审查和优化告警规则

## 📞 支持与反馈

### 获取帮助

#### 内部资源
- **文档索引**：`docs/README.md`
- **常见问题**：`docs/user/faq.md`
- **故障排除**：`docs/user/troubleshooting.md`

#### 社区支持
- **问题反馈**：在项目issue页面提交问题
- **功能建议**：提交功能请求issue
- **贡献指南**：查看`docs/user/contributing.md`

### 反馈渠道

#### 问题报告格式
```markdown
**问题描述**：
[清晰描述遇到的问题]

**复现步骤**：
1. [步骤1]
2. [步骤2]
3. [步骤3]

**期望结果**：
[描述期望的正常行为]

**实际结果**：
[描述实际发生的情况]

**环境信息**：
- OpenClaw版本： [版本号]
- 操作系统： [系统版本]
- Python版本： [Python版本]
- 相关配置： [相关配置信息]

**附加信息**：
[日志、截图等其他有用信息]
```

#### 功能建议格式
```markdown
**功能名称**：
[建议的功能名称]

**功能描述**：
[详细描述功能需求和预期效果]

**使用场景**：
[描述该功能的使用场景和用户群体]

**优先级**：
[高/中/低]

**相关功能**：
[与现有功能的关联性]

**实现建议**：
[可选的实现思路或技术建议]
```

---

**最后更新**: 2026-04-19  
**版本**: 1.0  
**维护者**: OpenClaw文档团队  
**文档状态**: 活跃维护中  

> **提示**: 本指南将持续更新。建议定期查看`docs/user/`目录获取最新版本。