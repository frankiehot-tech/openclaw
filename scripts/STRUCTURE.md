# scripts/ 目录结构

## 目标结构

```
scripts/
├── queue/          # 队列管理（queue 相关逻辑）
├── monitor/        # 监控告警（monitor, alerter, heartbeat）
├── test/           # 测试文件（test_*.py）
├── maintenance/    # 维护操作（cleanup, archive, fix, backup）
├── deploy/         # 部署脚本（start/stop/status/watch .sh）
├── clawra/         # ClawRA 子系统（外部集成）
└── legacy/         # 待废弃文件（留作参考）
```

## 文件映射

### queue/ (队列管理)
- `queue_monitor.py` — 队列监控主程序
- `check_queue_progress.py` — 队列进度检查
- `archive_completed_queues.py` — 已完成队列归档
- `sync_queue_manifest_status.py` — 队列清单状态同步
- `update_manifest_status.py` — 清单状态更新
- `two_minute_queue_monitor.py` — 2分钟队列巡检
- `workflow_state.py` — 工作流状态
- `generate_task_id.py` — 任务ID生成
- `monitor_gene_management.py` — 基因队列管理监控
- `start_gene_management_queue.sh` — 启动基因管理队列

### monitor/ (监控告警)
- `error_rate_alerter.py` — 错误率告警
- `availability_monitor.py` — 可用性监控
- `process_monitor.py` — 进程监控
- `performance_monitor.py` — 性能监控
- `performance_analyzer.py` — 性能分析
- `performance_benchmark.py` — 性能基准
- `collect_performance_metrics.py` — 性能指标采集
- `collect_stability_metrics.py` — 稳定性指标采集
- `traffic_switch_monitor.py` — 流量切换监控
- `checkpoint_monitor.py` — 检查点监控
- `two_minute_queue_monitor.py` — 2分钟巡检
- `gate_check.py` — 门禁检查

### test/ (测试文件)
- 所有 `test_*.py` 文件 (36个)
- `chaos_test_scenarios.yaml` — 混沌测试场景
- `conftest.py` — 测试共享配置

### maintenance/ (维护操作)
- `cleanup_stale_heartbeats.py`
- `remove_ghost_dependencies.py`
- `update_archive_index.py`
- `update_document_index.py`
- `distill_completed.py`
- `fix_*.py` 文件 (12个)
- `gene_management_queue_setup.py`
- `scan_approval_folder.py`
- `validate_document_format.py`

### deploy/ (部署脚本)
- 所有 `start_*.sh` 文件
- 所有 `stop_*.sh` 文件
- 所有 `status_*.sh` 文件
- 所有 `watch_*.sh` 文件
- `run_*.sh` 文件
- `install_*.sh` 文件
- `health_smoke.sh`
- `bootstrap_smoke_test.sh`

### 核心文件 (留驻 scripts/ 根目录 — Phase 2D 处理)
- `athena_ai_plan_runner.py` (4868行) — AI计划队列运行器 (Phase 2D 拆分)
- `rebuild_aiplan_priority_queues.py` (2062行) — 队列重建 (Phase 2D 拆分)
- `athena_web_desktop_compat.py` (2051行) — Web桌面兼容层 (Phase 2D 拆分)
- `openclaw_roots.py` — 共享路径定义 (被所有核心文件引用)
- `system_resource_facts.py` — 系统资源信息
- `codex_opencode_tuning_implementation.py` (1475行) — CodeX调优
- `athena_queue_deep_audit.py` (979行) — 队列深度审计
- `openhuman_24h_stress_runner.py` (876行) — 压力测试运行器

## 迁移说明

1. Phase 2D 完成核心文件拆分后, 逐步移入对应子目录
2. 迁移前先修复 `sys.path.insert` / import 路径引用
3. 旧位置保留 symlink 指向新位置（兼容期 2 周）
4. 阶段迁移: 测试文件 → 部署脚本 → 监控文件 → 队列文件 → 维护文件
