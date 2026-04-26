# 贡献指南

## 项目结构

本项目由两层组成：

- **OpenClaw** — AI 智能体工作流执行引擎（本仓库）
- **OpenHuman** — 碳硅共生协议（上层协议）

## 开发环境

```bash
git clone https://github.com/frankiehot-tech/openclaw.git
cd openclaw
pip install -e .
cp .env.example .env  # 编辑填入 API Key
```

## 提交规范

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档变更
- `chore:` 工具/配置变更
- `security:` 安全修复

## 代码规范

- Python 3.11+
- 遵循 ruff 配置
- 提交前运行 `pytest tests/`

## License

AGPL-3.0
