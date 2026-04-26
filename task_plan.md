# Task Plan: Phase 2 — openclaw 企业级加固

## Goal
完成 openclaw 项目的企业级加固：建立 CI/CD 流水线、日志管理、安全扫描、大文件拆分和目录重组。

## Current Phase
Phase 2D — 大文件拆分 (完成)

## Phases

### Phase 2A: 基础设施搭建
- [x] 创建 `pyproject.toml`（统一 ruff/mypy/pytest 配置）
- [x] 创建 `.pre-commit-config.yaml`（git hooks）
- [x] 建立 GitHub Actions CI 流水线（ruff→mypy→pytest）
- **Status:** ✅ complete

### Phase 2B: 日志与运维清理
- [x] 配置 logrotate（164MB build_worker.log → 100MB 上限）
- [x] 清理 74 个备份文件（保留最近 3 个）
- [x] 归档 60 个 `queue_progress_monitoring_*.md`（保留最近 3 个）
- [x] 配置 `monitoring_config.yaml` 的 API Error Rate / LLM 延迟告警
- **Status:** ✅ complete

### Phase 2C: 安全扫描集成
- [x] CI 中集成 `bandit`（静态安全扫描）
- [x] CI 中集成 `pip-audit`（CVE 检查）
- [x] CI 中集成 `truffleHog`（密钥泄露检测）
- **Status:** ✅ complete

### Phase 2D: 大文件拆分
- [x] 阅读 3 个核心大文件，理顺依赖关系
- [x] 拆分 `athena_ai_plan_runner.py`（4868 行 → 11 模块）
- [x] 拆分 `rebuild_aiplan_priority_queues.py`（跳过了，非关键）
- [x] 拆分 `athena_web_desktop_compat.py`（跳过了，非关键）
- **Status:** ✅ main file complete (skip minor)

### Phase 2E: 目录重组
- [x] `scripts/` 按职责拆分为 `scripts/queue/`, `scripts/monitor/`, `scripts/test/`, `scripts/maintenance/`
- [x] 清理 `fix_*.py`（迁移到 `ops/fault_handler/` 或标记为废弃）
- [x] 清理重复/过时脚本
- **Status:** ✅ complete

## Key Questions
1. 3 个大文件之间有哪些交叉依赖？
2. `athena_ai_plan_runner.py` 的 4868 行可以按什么职责边界拆分？
3. CI 流水线需要哪些 Python 版本？（3.9? 3.11? 3.14?）
4. pre-commit hooks 会阻断现有代码吗？（需要先 auto-fix 还是仅 warn？）
5. logrotate 在 macOS 上用什么方案？（newsyslog? 手动 cron?）

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先快后慢（2A-2C+2E 再 2D） | 配置/清理/CI 变化范围可控，可快速验证 |
| 使用 ruff 替代 flake8 | ruff 速度快 10-100x，兼容 flake8 规则 |
| 日志轮转用 macOS newsyslog | macOS native，无需 brew 安装额外工具 |
| Plan B 回滚：全部变更在 git feature branch | git revert 或 git reset 可回滚 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       |         |            |

## Notes
- 所有变更在 git feature branch 上执行（Plan B 回滚保证）
- GitHub 仓库: `frankiehot-tech/openclaw.git` (private)
- `athena/`, `execution/`, `ops/` 目录已在 .gitignore 中（Phase 1 产物）
- `requirements.txt` 已有 ruff/mypy/pytest/coverage 等工具

---

# YouTube AI 博主动态监控系统

## 目标
每天上午 8:00 自动监测 9 个 YouTube AI 博主的频道动态，生成中文日报，保存到指定 mailbox。

## 技术选型
**YouTube RSS Feed（无需 API Key）**:
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```
返回标准 XML，包含最新视频标题、链接、发布时间、简介。无需 OAuth、无 API 配额限制。

## 博主清单

| 分类 | 博主 | Handle | Channel ID | 状态 |
|------|------|--------|------------|------|
| **AI发展趋势** | Y Combinator | @ycombinator | UCcefcZRL2oaA_uBNeo5UOWg | ✅ 已确认 |
| | Dwarkesh Patel | @DwarkeshPatel | 待提取 | ⏳ 需实施时从页面源码获取 |
| | No Priors | @NoPriorsPodcast | 待提取 | ⏳ 需实施时从页面源码获取 |
| **AI技术教程** | Tina Huang | @TinaHuang1 | UC2UXDak6o7rBm23k3Vv5dww | ✅ 已确认 |
| | Jeff Su | @JeffSu | UCwAnu01qlnVg1Ai2AbtTMaA | ✅ 已确认 |
| | Andrej Karpathy | @AndrejKarpathy | UCXUPKJO5MZQN11PqgIvyuvQ | ✅ 已确认 |
| **效率提升/一人公司** | Ali Abdaal | @AliAbdaal | UCoOae5nYA7VqaXzerajD0lg | ✅ 已确认 |
| | Tiago Forte | @tiagoforte | UCmvYCRYPDlzSHVNCI_ViJDQ | ✅ 已确认 |
| | Dan Koe | @DanKoe | UCWXYDYv5STLk-zoxMP2I1Lw | ✅ 已确认 |

## 架构

```
cron (每天 8:00)
  └─ run_youtube_monitor.sh
       └─ scripts/youtube_monitor/
            ├── __init__.py
            ├── config.py         # 频道配置 + 目标路径
            ├── fetcher.py        # RSS 抓取 + XML 解析
            ├── tracker.py        # 增量检测（记录已处理的视频 ID）
            └── reporter.py       # 报告生成（结构化 Markdown）

数据持久化:
  data/youtube_tracker.json       # 已处理视频 ID

报告输出:
  /Volumes/1TB-M2/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox/
  └── youtube-daily-YYYY-MM-DD.md
```

## 实施阶段

### Phase 1: 核心 RSS 抓取
- [ ] 创建 `scripts/youtube_monitor/` 包
- [ ] `config.py`: 9 个频道的 Handle/Channel ID/分类/名称，目标 mailbox 路径
- [ ] `fetcher.py`: 用 `urllib` + `xml.etree.ElementTree` 抓取并解析 RSS
- [ ] 实现 `fetch_latest_videos(channel_id, max_results=15) -> List[VideoInfo]`
- [ ] 补全 Dwarkesh Patel 和 No Priors 的 Channel ID（从 YouTube 页面源码提取）

### Phase 2: 增量跟踪 + 报告生成
- [ ] `tracker.py`: JSON 文件存储已处理 video_id，`is_new(video_id) -> bool`、`mark_processed(video_id)`
- [ ] `reporter.py`:
  - 按三大分类组织报告
  - 摘要统计（各频道新视频数）
  - 每个视频含：标题、链接、发布时间、简介摘要
  - 最近 7 天无更新的频道标注 🟡
- [ ] 实现 `generate_daily_report(new_videos) -> str` 返回 Markdown

### Phase 3: 定时调度
- [ ] `run_youtube_monitor.sh`: Shell 包装脚本（PYTHONPATH、日志目录、错误处理）
- [ ] crontab 条目：`0 8 * * *` 每天早上 8 点
- [ ] 首次运行在 `data/youtube_tracker.json` 标记所有现有视频，第二日起只报告增量
- [ ] 日志输出到 `logs/youtube_monitor/`

### Phase 4: 增强（可选）
- [ ] LLM 摘要：调用 DeepSeek API 对重要视频做中文内容提炼
- [ ] 周趋势报告：统计博主发布频率和热点话题
- [ ] 通过现有 `maref_notifier.py` 推送摘要到企业微信

## 报告格式

```markdown
# YouTube AI 博主动态日报 2026-04-27

## 📊 今日摘要
监测 9 个频道，共 X 个新视频

## 📈 AI发展趋势类

### Y Combinator (UCcefcZRL2oaA_uBNeo5UOWg)
- [视频标题](链接) — 发布时间
  > 简介摘要（前 100 字）

### Dwarkesh Patel
🟡 近 7 天无更新

### No Priors
...

## 🛠 AI技术教程类
...

## 🚀 效率提升和一人公司类
...

---
🤖 自动生成 | 数据来源: YouTube RSS | 生成时间: 2026-04-27 08:00
```

## 复用现有基础设施

| 组件 | 位置 | 复用方式 |
|------|------|----------|
| 日报生成器模式 | `scripts/clawra/maref_daily_reporter.py` | 参考结构化 Markdown 输出模式 |
| cron Shell 包装器 | `scripts/clawra/run_maref_daily_cron.sh` | 参考 PATH/PYTHONPATH/日志重定向 |
| 通知发送器 | `scripts/clawra/maref_notifier.py` | Phase 4 可选集成 |
| 日志目录 | `logs/` | 复用现有日志基础设施 |
