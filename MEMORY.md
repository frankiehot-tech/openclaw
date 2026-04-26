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

## OpenHuman-Athena-AutoResearch (蒸馏于 2026-04-20)

- **queue_item_id**: athena_autoresearch_engine_skeleton
- **阶段**: build
- **源文档**: 003-open human/007-AI-plan/completed/OpenHuman-Athena-AutoResearch-基础优化引擎原型与约束骨架-VSCode执行指令.md
