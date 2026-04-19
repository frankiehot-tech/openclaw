# OpenClaw 快速开始指南

## 🚀 立即开始

欢迎使用OpenClaw！本指南将帮助你快速设置和运行这个工程化AI开发平台。

### 环境配置

#### 1. 设置环境变量
```bash
# 设置OpenClaw项目根目录
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"

# 设置Athena运行时根目录（通常与OPENCLAW_ROOT相同）
export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"

# 添加到PATH方便访问脚本
export PATH="$OPENCLAW_ROOT/scripts:$PATH"

# 持久化配置（推荐添加到~/.zshrc或~/.bashrc）
echo 'export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"' >> ~/.zshrc
echo 'export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"' >> ~/.zshrc
echo 'export PATH="$OPENCLAW_ROOT/scripts:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### 2. 验证环境配置
```bash
# 运行环境验证脚本
python3 setup_environment.py

# 验证路径配置完整性
python3 validate_path_config.py
```

### 项目结构导航

#### 核心目录
```
openclaw/
├── .openclaw/                    # OpenClaw运行时状态目录
├── scripts/                      # 核心脚本目录
│   ├── queue_monitor.py          # 队列监控脚本
│   ├── validate_path_config.py   # 路径验证脚本
│   └── queue_monitor_dashboard.py # 监控仪表板
├── config/                       # 配置文件目录
│   └── paths.py                  # 单一事实源的路径配置
├── docs/                         # 文档根目录（三才六层模型）
│   ├── architecture/             # 架构层文档
│   ├── technical/                # 技术层文档
│   ├── audit/                    # 审计层文档（按年月组织）
│   └── user/                     # 用户层文档（本目录）
├── skills/                       # 智能体技能定义（保持原结构）
├── vendor/                       # 第三方依赖文档
└── task_plan.md                  # 当前任务计划跟踪文件
```

#### 重要文件
- **CLAUDE.md** - Claude Code项目配置
- **README.md** - 项目主说明文档
- **task_plan.md** - 实时任务计划跟踪
- **progress.md** - 进度记录文件
- **findings.md** - 研究发现记录

### 🧠 核心概念理解

#### MAREF三才六层模型
OpenClaw采用MAREF（多智能体递归进化框架）的三才六层模型组织系统：

| 层级 | 目录 | 文档示例 |
|------|------|----------|
| **战略层** | `docs/architecture/` | 认知DNA、智能体架构、系统设计 |
| **管理层** | `docs/technical/specifications/` | 技术规范、接口定义 |
| **流程层** | `docs/technical/operations/` | 运维文档、操作指南 |
| **应用层** | `docs/technical/deployment/` | 部署指南、配置说明 |
| **平台层** | `docs/audit/` | 审计报告、性能分析 |
| **环境层** | `docs/user/` | 用户指南、快速开始 |

#### Athena队列系统
OpenClaw的核心是Athena队列系统，负责：
- **智能任务编排**：基于契约框架的任务分配
- **执行器路由**：SmartOrchestrator智能路由决策
- **状态同步**：原子状态更新确保一致性
- **监控告警**：实时队列健康度监控

### 📖 文档系统使用

#### 1. 文档导航
```bash
# 查看完整文档索引
cat docs/README.md

# 查找特定类型文档
ls docs/architecture/           # 架构文档
ls docs/technical/operations/   # 运维文档
ls docs/audit/2026-04/          # 2026年4月审计文档

# 使用文档搜索
grep -r "Athena队列" docs/      # 搜索相关内容
```

#### 2. 新文档创建
创建新文档时应遵循：
- **命名规范**：英文优先，YYYY-MM-DD日期格式，短横线分隔
- **分类位置**：按三才六层模型放入对应目录
- **内容结构**：清晰的问题-解决方案格式

示例：
```bash
# 创建新的运维文档
cp templates/operations-template.md docs/technical/operations/new-operation-guide.md

# 创建审计报告
echo "# 审计报告" > docs/audit/$(date +%Y-%m)/new-audit-report.md
```

### 🔧 日常操作

#### 1. 队列管理
```bash
# 启动队列监控
python3 scripts/queue_monitor.py --config queue_monitor_config.yaml

# 查看队列状态
python3 scripts/queue_monitor_dashboard.py

# 访问监控仪表板
# 浏览器打开: http://localhost:5002
```

#### 2. 任务计划管理
```bash
# 查看当前任务计划
cat task_plan.md | head -30

# 更新任务进度
# 编辑task_plan.md更新任务状态

# 记录进度
echo "$(date): 完成任务X" >> progress.md
```

#### 3. 环境验证
```bash
# 定期验证环境配置
python3 validate_path_config.py

# 检查系统健康度
python3 scripts/queue_monitor.py --health-check
```

### 🚨 故障排除

#### 常见问题

**问题1：环境变量不生效**
```bash
# 检查当前环境变量
echo $OPENCLAW_ROOT
echo $ATHENA_RUNTIME_ROOT

# 重新加载配置
source ~/.zshrc
# 或直接设置
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"
```

**问题2：路径配置验证失败**
```bash
# 检查paths.py配置
cat config/paths.py

# 重新运行验证脚本
python3 validate_path_config.py --verbose
```

**问题3：队列监控仪表板无法访问**
```bash
# 检查仪表板进程
ps aux | grep queue_monitor_dashboard

# 重启仪表板
cd scripts
python3 queue_monitor_dashboard.py &
```

### 📚 学习路径

#### 新手（1-3天）
1. **第一天**：环境配置 → 运行验证脚本 → 熟悉项目结构
2. **第二天**：阅读核心文档 → 理解MAREF框架 → 学习三才六层模型
3. **第三天**：尝试基础操作 → 队列监控 → 任务计划管理

#### 中级用户（1-2周）
1. **第一周**：深入Athena队列系统 → 学习智能路由 → 理解契约框架
2. **第二周**：参与实际任务 → 创建审计文档 → 配置监控告警

#### 高级用户（1个月+）
1. **系统扩展**：自定义智能体 → 扩展执行器 → 优化路由算法
2. **架构改进**：参与MAREF框架演进 → 设计新契约 → 性能优化

### 🔗 相关资源

#### 内部文档
- [项目架构](architecture/system-design.md) - 完整系统架构设计
- [技术规范](docs/technical/specifications/) - 详细技术规范文档
- [运维手册](technical/operations/operations-manual.md) - 日常运维指南
- [用户指南](user/user-guide.md) - 完整用户功能说明

#### 外部参考
- [MAREF框架文档](architecture/maref-smart-workflow-design.md) - MAREF设计理念
- [gstack决策框架](docs/architecture/gstack-integration.md) - 工程化决策原则
- [Claude Code配置](CLAUDE.md) - Claude Code项目配置

### 🎯 下一步

1. **配置监控告警**：编辑`queue_monitor_config.yaml`设置邮件/Slack通知
2. **了解高级功能**：阅读[用户指南](user/user-guide.md)掌握所有功能
3. **参与项目贡献**：查看[贡献指南](user/contributing.md)参与开发

---

**最后更新**: 2026-04-19  
**维护者**: OpenClaw文档团队  
**反馈**: 更新此文档或在`docs/user/`目录创建改进建议