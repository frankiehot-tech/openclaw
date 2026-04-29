# MEMORY.md — openclaw 长期记忆

## 企业级工作流状态 (2026-04-26)

- **Phase 1**: ✅ 全局 Claude Code hooks (SessionStart / PreToolUse / PostToolUse) + keybindings
- **Phase 2**: ✅ 003-open human 项目企业级补强 (CLAUDE.md v1.2, CI/CD, Git init)
- **Phase 3**: ✅ openclaw 深度加固 (pre_commit hook, 6 skills 注册, CI 硬阻断)
- **Phase 4**: ✅ 跨项目知识桥接 (CROSS_PROJECT.md, skills_health_check.py, MCP 扩展)
- **分支**: phase2-enterprise-hardening → main (已合并)
- **综合评分**: 4.4/10 → 7.8/10

## 项目架构

- **openclaw** = 代码/CI/引擎层
- **003-open human** = 协议/文档/方法论层
- 双项目对齐，通过 wiki/CROSS_PROJECT.md 桥接

## 关键配置路径

- 全局 hooks: `~/.claude/hooks/` (session_start, destructive_warn, change_tracker)
- 项目 hooks: `.claude/hooks/pre_commit.py` (ruff + mypy)
- 技能注册: `.claude/skills/` (7 skills: ui-ux-pro-max + 6 openhuman skills)
- CI: `.github/workflows/ci.yml` (lint + typecheck + test + security, 全部硬阻断)
- MCP: `~/.claude/settings.json` (ai-tools + context7 + deepwiki)

## 语言偏好 (2026-04-26)

- 用户要求默认使用中文回复
- 所有输出用中文，不再用英文
- 此规则严格执行

## 全量代码库审计 (2026-04-27)

### 成果
- 发现并修复 ~23,028 项 Ruff 可检测问题（语法错误、未定义名称、裸 except、未使用导入等）
- 修复 26 处硬编码绝对路径（agent_system/ 全模块）
- 全量 ruff format 格式化（446 文件）
- **剩余 137 项**：低优先风格优化（E402 import位置/B007 循环变量/SIM102 可折叠if），不影响运行

### 关键架构决策
1. SAST+LLM 双层审计架构（Ruff 规则层 → LLM 语义层）
2. 第三方目录排除策略（scripts/clawra/ 等不在核心质量指标中）
3. 采纳 llm-wiki 模式：wiki/ 内容已全面更新，后续会话自动写入

### 需要你操作
- API 密钥轮换：DashScope/DeepSeek/Anthropic 控制台

### 保留知识
- DASHSCOPE_API_KEY 已更新为新密钥
- DeepSeek/Anthropic API 不再使用，已从 .env.example 注释
- .env 从未被 Git 跟踪（gitignore 正确配置）

## OpenHuman-Athena-AutoResearch (蒸馏于 2026-04-20)

- **queue_item_id**: athena_autoresearch_engine_skeleton
- **阶段**: build
- **源文档**: 003-open human/007-AI-plan/completed/OpenHuman-Athena-AutoResearch-基础优化引擎原型与约束骨架-VSCode执行指令.md
