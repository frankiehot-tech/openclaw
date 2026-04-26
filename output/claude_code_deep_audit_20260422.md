# Claude Code / DashScope 本地深度审计报告

日期: 2026-04-22
工作区: `/Volumes/1TB-M2/openclaw`

## 执行摘要

这次审计确认了一件最关键的事：你机器上现在并不是“单一一套 Claude Code 配置”在运行，而是至少有四层并存。

1. 真正执行的 CLI 本体是 Homebrew 全局安装的 `@anthropic-ai/claude-code@2.1.117`
2. 你平时在交互式 `zsh` 里敲的 `claude`，默认会先进入 `/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh`
3. `~/.claude/settings.local.json` 又把运行时指向了 `http://localhost:8080`
4. `localhost:8080` 后面是一个自写的 `dashscope-adapter.py`，它把 Anthropic Messages API 转成 DashScope 的 OpenAI 兼容接口

所以当前的真实问题不是“代理没修好”，而是“活动链路、历史脚本、会话层、验证脚本没有收敛到同一套架构”。这导致你一部分会话已经能正常工作，另一部分仍然会沿着旧路径或旧假设报错。

## 多目录角色归类

| 路径 | 角色 | 当前状态 | 结论 |
|------|------|----------|------|
| `/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code` | 官方 CLI 本体 | 活跃 | 实际执行二进制来源 |
| `/Volumes/1TB-M2/openclaw/claude-code-setup` | 本地包装层/代理层/测试脚本集合 | 活跃 | 真正影响你交互式启动行为 |
| `/Volumes/1TB-M2/openclaw/Projects/claude-code-router` | 第三方路由项目源码 | 非运行态 | 已安装但当前未作为主链路使用 |
| `/Volumes/1TB-M2/claude-code` | 研究/备忘/恢复脚本目录 | 非运行态 | 更多像知识和草稿集 |
| `/Volumes/1TB-M2/claude-code/claude-code-reconstructed` | “reconstructed”目录 | 非运行态 | 里面只有一个空文件 `claude`，不是可运行源码树 |

结论：你说的“本地有多个 Claude Code 文件夹”是成立的，但真正会影响运行结果的，主要是 `Homebrew CLI + ~/.claude + claude-code-setup` 这一条链。`claude-code-router` 和 `reconstructed` 目录目前更像旁路或历史产物。

## 当前真实启动链路

### 非交互环境

- `command -v claude` 指向 `/opt/homebrew/bin/claude`
- 实际包版本是 `2.1.117`

### 交互式 zsh 环境

- `type claude` 显示：
  - `claude is an alias for /Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh`
- `.zshrc` 中存在多组重复别名：
  - `alias claude='/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh'`
  - `alias claude-qwen='/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh 3'`
  - `alias claude-bailian='/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh 5'`

### 推荐启动脚本

- `/Volumes/1TB-M2/openclaw/claude-code-setup/start-claude.sh` 才是你总结里那套“先确保代理，再 export `ANTHROPIC_BASE_URL=http://localhost:8080`，最后启动 Claude”的实现
- 但这个脚本并没有被 `claude` 默认别名使用

结论：你现在文档里推荐的启动方式，和你 shell 里默认 `claude` 的实际行为，不是同一条路径。

## 当前配置现状

### 已确认有效的部分

- `~/.claude/settings.local.json` 当前内容为：
  - `ANTHROPIC_BASE_URL=http://localhost:8080`
  - `ANTHROPIC_MODEL=qwen3.6-plus`
- 本地适配器进程正在运行：
  - `Python /Volumes/1TB-M2/openclaw/claude-code-setup/dashscope-adapter.py`
- `127.0.0.1:8080` 正在监听
- 实测通过：
  - `GET /`
  - `GET /v1/models`
  - `HEAD /v1/models`
  - `POST /v1/messages?beta=true`

### 未收敛的部分

- `claude-dual-model.sh` 仍默认导出：
  - `ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 而不是 `http://localhost:8080`
- `claude-config.sh` 的主分支仍以 DashScope 直连兼容地址为中心
- `start-claude.sh` 和 `settings.local.json` 用的是“本地代理架构”
- `claude-dual-model.sh` 和一批测试脚本用的是“DashScope 直连兼容模式”

结论：你当前同时保留了两套架构。

1. 直连 DashScope 兼容接口
2. 通过本地代理转 Anthropic 协议

这就是最典型的配置漂移。

## 代理层深度审计

当前活跃代理文件是：

- `/Volumes/1TB-M2/openclaw/claude-code-setup/dashscope-adapter.py`

它当前的关键特征：

1. 只公开一个模型：
   - `qwen3.6-plus`
2. 已支持：
   - `/v1/messages`
   - `/v1/messages?beta=true`
3. 向下游发送：
   - `POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
4. 当前是“硬编码单模型适配器”：
   - 传入任何模型，最终都按 `MODEL_NAME = "qwen3.6-plus"` 发送

### 已验证的成功点

- 你总结里的“路径问题”和“模型名基础问题”在当前活跃代理上基本已经修到可用状态
- `POST /v1/messages?beta=true` 现在能跑通

### 仍存在的设计缺口

1. 只支持单模型暴露
2. 只做最小 `/v1/messages` 适配，没有做完整 Anthropic API 面覆盖
3. 失败时错误处理不稳
4. 日志过于详细，泄露鉴权头

## 运行态稳定性审计

我统计了 `/tmp/dashscope-adapter.log` 中最近一轮 `/v1/messages?beta=true` 请求：

- 总体：
  - `200`: 36
  - `500`: 30

- 按请求模型分布：
  - `qwen3.6-plus`: `req=36`, `200=29`, `500=7`
  - `claude-haiku-4-5-20251001`: `req=30`, `200=7`, `500=23`

### 这说明什么

1. 代理“不是完全挂了”
   - Qwen 主链路大多数请求能成功
2. 代理“也远远算不上稳定”
   - 最近样本里整体 500 占比很高
3. 内部还有一类 `claude-haiku-4-5-20251001` 请求在走你的本地代理

从请求体看，这些 `claude-haiku-4-5-20251001` 请求大多是 Claude Code 自己的标题生成/元任务请求。也就是说，即便主会话设成了 Qwen，Claude Code 仍可能在内部发起“小模型任务”。你当前的代理没有区分这些请求，只会一律压到 `qwen3.6-plus`。

这本身不一定必然出错，但会带来两个后果：

1. 小模型内部任务的耗时和行为被强制改写
2. 一旦这些请求超时，CLI 看起来就会出现“偶发卡住/偶发失败”

## 当前最像根因的问题

## 1. 启动入口不统一

`claude` 默认别名走 `claude-dual-model.sh`，但你当前可工作的架构却是 `settings.local.json + localhost:8080 + dashscope-adapter.py`。

这意味着：

- 文档说一套
- 别名跑一套
- 代理又是一套

结果就是你改对了一处，另一处又把行为拖回旧路径。

## 2. 历史残留没有清干净

在 `/Volumes/1TB-M2/openclaw/claude-code-setup` 中：

- `qwen3.6-plus-2026-04-02` 仍残留在 4 个文件里
- `https://dashscope.aliyuncs.com/compatible-mode/v1` 仍出现在 22 个文件里
- `http://localhost:8080` 只出现在 7 个文件里

这说明“代理模式”并没有成为唯一事实来源。

## 3. 适配器的异常处理有缺陷

日志里已经出现了明确栈：

- 下游 DashScope 超时
- `requests.post(... timeout=30)` 抛 `ReadTimeout`
- 适配器随后执行 `self.send_error(500, f"请求DashScope失败: ...")`
- `http.server` 在写中文 reason phrase 时触发 `UnicodeEncodeError`

这意味着：

1. 真正的超时问题没有被正常转换成稳定的 JSON 错误
2. 代理自己的错误处理又二次崩掉
3. CLI 侧看到的 500 可能比真实错误更难诊断

## 4. 安全面明显不达标

我没有在报告里复述完整密钥，但统计结果很清楚：

- `claude-code-setup` 内部出现 `51` 处疑似明文密钥引用
- `~/.claude/settings.local.json` 有 `1` 处
- `~/.zshrc` 有 `6` 处

更严重的是：

- `/tmp/dashscope-adapter.log` 正在打印 `Authorization` 和 `x-api-key`
- 也就是说，密钥不仅硬编码在文件里，还会落进日志

这已经不是“风格不好”，而是实际安全风险。

## 历史错误的复盘结论

从 `~/.claude/projects/*.jsonl` 可以确认，你之前遇到过的报错是真实发生过的：

- `There's an issue with the selected model (qwen3.6-plus).`
- 更早还有：
  - `dashscope/qwen-plus`
  - `dashscope/qwen3-plus`

从历史 debug 记录还能看到老问题的典型形态：

- 请求路径变成 `/compatible-mode/v1/v1/messages`
- 返回 404

这和你总结里的“协议不匹配 + 路径拼接错误”是完全一致的。

结论是：

- 旧问题不是幻觉
- 新问题也不是同一个问题的简单延续
- 你现在已经从“必然 404”进化到“主链路能跑，但旁路和稳定性仍有明显缺口”

## 优先级判断

### P0: 必须先处理

1. 统一启动入口
   - 要么默认只走 `start-claude.sh`
   - 要么让 `claude-dual-model.sh` 彻底改成代理模式
   - 但不能两套并存

2. 停止日志打印密钥并准备轮换
   - `dashscope-adapter.py` 的请求头 debug 需要立刻降敏
   - 已暴露到脚本、文档、日志中的密钥建议轮换

3. 修补代理超时错误处理
   - 错误 reason phrase 不能带中文
   - 应返回稳定 JSON body，而不是让 `send_error` 再崩一次

### P1: 很快要处理

1. 清除 `qwen3.6-plus-2026-04-02` 残留
2. 清理 `claude-code-setup` 中仍指向直连 `compatible-mode/v1` 的脚本
3. 明确内部 `claude-haiku-*` 请求如何路由
   - 接受它们统一落到 Qwen
   - 或做显式映射/降级策略

### P2: 结构化收尾

1. 给各目录加“角色说明”
2. 把 `reconstructed` 空目录和无效研究脚本归档
3. 如果确实要长期保留多方案，建立一个单一入口清晰切换

## 我对现状的结论

当前状态不是“完全坏了”，而是“主通路已经打通，但系统仍处于半收敛状态”。

更具体一点：

1. 主会话用 `qwen3.6-plus` 经过本地代理，已经可以工作
2. 旧的直连 DashScope 方案和旧模型名残留还在污染环境
3. 背景小模型请求也会打进代理，造成额外不稳定因素
4. 安全面比功能面更紧急，尤其是明文密钥和日志泄露

如果你接下来要我继续推进，最合理的下一步不是再“猜哪里坏”，而是做一次收敛式整理：

1. 只保留一条启动链
2. 只保留一套模型名
3. 只保留一套代理模式
4. 清理并轮换密钥
5. 修补代理超时错误路径

这样后面的任何调试才不会继续被历史残留反向污染。
