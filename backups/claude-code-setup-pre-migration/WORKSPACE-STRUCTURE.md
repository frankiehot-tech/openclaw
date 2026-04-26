# AI Assistant Workspace Structure

当前只保留一个主目录作为有效入口：

- 主目录：`/Users/frankie/claude-code-setup`
- 官方 CLI：`/opt/homebrew/bin/claude`
- 默认入口脚本：`/Users/frankie/claude-code-setup/claude-dual-model.sh`
- 一键启动脚本：`/Users/frankie/claude-code-setup/start-claude.sh`
- 本地 LLM 适配器：`/Users/frankie/claude-code-setup/dashscope-adapter.py`

## 目录角色

- `reference/claude-code-best-practice`
  - 原来的最佳实践仓库
  - 现在仅作为参考资料保留

- `archive/claude-code-research`
  - 原来的研究/恢复资料目录
  - 现在仅作为归档保留

## 当前推荐启动方式

1. 在终端里直接运行 `claude`
2. 如果要强制走默认 Qwen 适配链路，运行：
   - `/Users/frankie/claude-code-setup/start-claude.sh`
3. 如果要显式走智能路由，运行：
   - `/Users/frankie/claude-code-setup/claude-dual-model.sh`

## 当前统一链路

`claude` / `start-claude.sh`
-> `claude-dual-model.sh`
-> `claude-config.sh`
-> `dashscope-adapter.py` (自动启动 + 轮询等待)
-> DashScope OpenAI Compatible API

## 变更日志

### 2026-04-22

- **收敛完成**: 统一启动入口，`claude` 别名稳定指向 `claude-dual-model.sh`
- **适配器增强**: 启动等待从固定 2 秒改为轮询重试（最多 15 秒）
- **安全硬化**: 停止在启动信息中打印密钥（即使是脱敏版本）
- **旧模型名清理**: 移除 `qwen3.6-plus-2026-04-02` 残留映射

## 注意

- 目前没有保留任何"泄露源码版本"作为运行入口。
- 目前没有把参考库或研究目录继续暴露为 shell 入口。
- 现在的运行版本是官方 Homebrew CLI 配合本地协议适配层。