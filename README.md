# OpenClaw · AI 智能体开发平台

> 让一个人 + AI = 一家公司。

## 简介

OpenClaw 是一个开源的 AI 智能体工作流引擎，专为 **一人公司（OPC）** 创业模式设计。
通过本地部署的 AI Agent 编排系统，个人开发者可以独立完成代码生成、文档审计、
自动化测试等复杂工程任务。

本项目是深圳市龙岗区"龙虾十条"政策重点支持的开源项目。

## 核心特性

- **MAREF 多智能体递归进化框架**：基于 64 卦状态机的治理系统
- **四级生存模式**：normal / low / critical / paused 预算自适应
- **Athena 工作流引擎**：任务队列 + 自动分类 + 质量门禁
- **财务熔断器**：$5/日强制安全边界
- **多模型支持**：DeepSeek / Claude / Qwen 自由切换

## 快速开始

```bash
git clone https://github.com/frankiehot-tech/openclaw.git
cd openclaw
pip install -e .
cp .env.example .env   # 编辑填入你的 API Key
python3 scripts/wallet_guardian.py
```

### 验证安装

```bash
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print('API Key:', os.environ.get('DASHSCOPE_API_KEY','')[:8]+'...')"
```

## 与 OpenHuman 协议的关系

OpenClaw 是 **执行引擎**，OpenHuman 是 **上层协议**。两者共同构成完整的人机混合劳动力市场基础设施。

```
OpenHuman 碳硅共生协议  ← 市场层（撮合、结算、确权）
        ↓
OpenClaw 智能体引擎    ← 执行层（工作流、Agent 编排、质量门禁）
```

→ [OpenHuman 碳硅共生协议](https://github.com/frankiehot-tech/openhuman)

## 项目架构

```
openclaw/
├── scripts/          # 执行入口与工具脚本
├── execution/        # Agent 运行时（runner、agents、harness）
├── ops/              # 运维监控（故障处理、部署）
├── athena/           # Athena 工作流引擎
├── contracts/        # 数据契约与质量门禁
├── docs/             # 文档体系
└── .env.example      # 环境变量模板
```

## 政策合作

本项目积极对接深圳市龙岗区"龙虾十条"政策，致力于构建 AI 智能体开源生态。

| 政策项 | 状态 |
|--------|------|
| 开源贡献奖励 | 申报中 |
| 数字员工应用券 | 筹备中 |
| 场景项目示范 | 规划中 |

## License

AGPL-3.0 License — 详见 [LICENSE](LICENSE)。
