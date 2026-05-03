# Wiki 操作日志

## 2026-05-03

- `[DEPLOY]` Claude Code: 部署 4 个 Karpathy Skill (autoresearch-loop, code-quality, simplicity, knowledge-bases)
- `[INTEGRATE]` OpenCode: AGENTS.md 追加 Karpathy 智能工作流集成段落（四原则+5维评分+ratchet loop+简洁检查）
- `[BRIDGE]` CROSS_PROJECT.md: 添加 Karpathy AutoResearch 研究文档索引 (11 文件)
- `[DECISION]` ADR-006: 采纳 Karpathy AutoResearch 工作流（手动/半自动→v0.2.0演进）
- `[RATCHET]` 5轮 ratchet loop: 726→142 ruff errors (-584, 80.4%), 全部 KEEP
- `[TECHDEBT]` PATTERNS.md: 记录 142 项已知技术债 (TD-001~004)
- `[CHORE]` .gitignore 加固: 排除 chrome-profiles/, .qianwen-auth/, .trae/documents/
- `[SESSION]` 写入 wiki/sessions/2026-05-03.md
- `[UPDATE]` MEMORY.md: 记录 Karpathy 部署状态
- `[VERIFY]` ruff 142 errors + pytest 120 passed
- `[OUTPUT]` results.tsv: ratchet loop 实验记录

## 2026-04-27

- `[AUDIT]` 全量代码库审计：发现 ~23,028 项问题
- `[FIX]` 136 处语法错误修复（Python 3.12 f-string 向后兼容等）
- `[FIX]` 26 处硬编码路径 → 相对路径
- `[FIX]` 126 处 F821 未定义名称 → 补全导入
- `[FIX]` 123 处 E722 裸 except → `except Exception:`
- `[FIX]` 2,204 处 F401 未使用导入 → 全部清理
- `[FIX]` 2,180 处 F541 伪 f-string → 自动修复
- `[FIX]` 469 处 F841 未使用变量 → 自动修复
- `[FIX]` 446 文件 ruff format → 全量格式化
- `[FIX]` 6,091 处 UP006 非 PEP585 注解 → 自动升级
- `[CONFIG]` TruffleHog 安全配置修复（fail:true）
- `[CONFIG]` pre-commit mypy 路径修复（绝对路径→mirror）
- `[CONFIG]` GitHub Actions 版本升级（v3→v4/v5）
- `[CONFIG]` pyproject.toml exclude 扩展 + src 扩展
- `[CONFIG]` `.env.example` 注释掉不再使用的 DeepSeek/Anthropic
- `[DECISION]` 采纳 SAST+LLM 双层审计架构（ADR-003）
- `[DECISION]` 第三方目录排除策略（ADR-004）
- `[DECISION]` 采用 llm-wiki 模式强化知识复利（ADR-005）
- `[SESSION]` 写入会话摘要 wiki/sessions/2026-04-27.md
- `[UPDATE]` 更新 INDEX.md、DECISIONS.md、PATTERNS.md、LOG.md
- `[REPORT]` 审计报告：audit_results/codebase_audit_report_20260427.md
- `[REPORT]` 技术评估报告：写入 015-mailbox/ 目录
- `[BRIDGE]` CROSS_PROJECT.md 全面重写：索引 ~40 个外部文档，覆盖 7 个目录
- `[CONFIG]` AGENTS.md 添加跨项目知识桥接段落
- `[UPDATE]` INDEX.md 扩展导航项（跨项目索引）
- `[TEST]` 新建 3 个测试文件：test_runner_utils (17), test_runner_manifest (11), test_runner_config (11) — 39 tests all pass
- `[FIX]` 修复 circular import in runner module (config ↔ utils, manifest ↔ executor ↔ failure)
- `[FIX]` 137→134 项剩余（自动修复 3 项 SIM/B018）
- `[REPORT]` 更新 CROSS_PROJECT.md → AGENTS.md → 索引全面打通
