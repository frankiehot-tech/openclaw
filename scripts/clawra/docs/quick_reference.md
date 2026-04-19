# MAREF生产系统快速参考

## 常用命令

### 启动系统
```bash
./start_maref_production.sh
```

### 停止系统
```bash
./stop_maref_production.sh
```

### 环境检查
```bash
python3 check_production_environment.py
```

### 健康检查
```bash
python3 health_check.py
```

### 查看日志
```bash
# 实时查看
tail -f logs/maref_production.log

# 搜索错误
grep -i error logs/maref_production.log

# 查看特定日期
tail -f logs/maref_production.log | grep "$(date +%Y-%m-%d)"
```

### 数据库管理
```bash
# 备份数据库
cp /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db /backup/maref_memory_$(date +%Y%m%d).db

# 检查表大小
sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT name, (pgsize/1024.0/1024.0) as size_mb FROM dbstat ORDER BY size_mb DESC LIMIT 10;"

# 检查数据量
sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT entry_type, COUNT(*) FROM memory_entries GROUP BY entry_type ORDER BY COUNT(*) DESC;"
```

### 监控相关
```bash
# 查看当前状态
python3 -c "from run_maref_daily_report import create_integration_environment; env = create_integration_environment(); print(f'当前卦象: {env.state_manager.current_state} ({env.state_manager.get_hexagram_name()})')"

# 查看性能指标
python3 -c "from maref_monitor import MAREFMonitor; m = MAREFMonitor(); print(m.collect_all_metrics())"
```

### 日报系统
```bash
# 手动生成日报
python3 run_maref_daily_report.py --mode production

# 生成集成模式日报（测试用）
python3 run_maref_daily_report.py --mode integration

# 查看日报生成历史
ls -la /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open\ human（碳硅基共生）/015-mailbox/maref-daily-*.md
```

## 关键文件位置

### 程序文件
- **主程序目录**: `/Volumes/1TB-M2/openclaw/scripts/clawra/`
- **部署脚本**: `start_maref_production.sh`, `stop_maref_production.sh`
- **检查脚本**: `check_production_environment.py`, `health_check.py`

### 数据文件
- **数据库**: `/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db`
- **内存目录**: `/Volumes/1TB-M2/openclaw/memory/maref/`
- **备份目录**: `/Volumes/1TB-M2/openclaw/scripts/clawra/backup/`

### 配置文件
- **生产配置**: `config/production_config.py`
- **性能基线**: `config/performance_baseline.py`
- **监控配置**: `config/monitor_config.py`

### 日志文件
- **生产日志**: `logs/maref_production.log`
- **日报日志**: `logs/maref_daily_report.log`
- **监控日志**: `logs/monitor_*.log`
- **错误日志**: `logs/error_*.log`

## 监控指标

### 系统健康
- **ROMA_MAREF_AVAILABLE**: 必须为True
- **智能体实例化成功率**: ≥95%
- **数据库连接状态**: 正常
- **进程运行状态**: 所有组件进程正常

### 性能指标（基于基线）
| 指标 | 警告阈值 | 紧急阈值 | 说明 |
|------|----------|----------|------|
| 状态转换响应时间 | 0.5ms | 1.0ms | 基于基线: 0.04-0.06ms |
| 内存使用率 | 70% | 80% | 基于基线: 最大76.4% |
| CPU使用率 | 60% | 70% | 基于基线: 最大41.7% |
| 控制熵H_c | 0.5 | 1.0 | 衡量状态分布多样性 |
| 格雷编码违规率 | 5% | 10% | 状态转换约束检查 |
| 智能体响应时间 | 10ms | 20ms | 智能体决策时间 |

### 业务指标
- **日报生成成功率**: 100% (每天上午9点自动生成)
- **预警准确率**: ≥95% (误报率≤5%)
- **系统可用性**: ≥99.5%
- **数据一致性**: 100%

## 告警处理流程

### 红色告警（紧急）
1. **立即检查**
   ```bash
   tail -n 100 logs/maref_production.log | grep -i "error\|critical\|red"
   python3 health_check.py
   ```

2. **系统状态检查**
   ```bash
   ./stop_maref_production.sh
   python3 check_production_environment.py
   ./start_maref_production.sh
   ```

3. **数据恢复**（如需）
   ```bash
   # 恢复最近备份
   cp /backup/maref_memory_latest.db /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db
   ```

### 黄色告警（警告）
1. **监控检查**
   ```bash
   # 查看最近告警
   grep -i "yellow\|warning" logs/maref_production.log | tail -20
   ```

2. **性能分析**
   ```bash
   # 检查资源使用
   top -n 1 | grep -E "python|maref"
   # 检查数据库性能
   sqlite3 /Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db "SELECT * FROM sqlite_master WHERE type='table';"
   ```

## 定期维护任务

### 每日任务
- [ ] 检查系统健康状态
- [ ] 验证日报生成
- [ ] 检查日志文件大小
- [ ] 确认预警系统正常

### 每周任务
- [ ] 运行完整健康检查
- [ ] 清理旧日志文件
- [ ] 备份数据库
- [ ] 检查磁盘空间

### 每月任务
- [ ] 性能基线审查
- [ ] 系统更新检查
- [ ] 安全审计
- [ ] 文档更新

## 紧急联系方式

### 技术支持
- **技术支持**: [联系人信息]
- **故障报告**: [报告渠道]
- **文档更新**: [文档仓库]

### 应急响应
1. **系统管理员**: [姓名/联系方式]
2. **开发团队**: [团队联系方式]
3. **业务负责人**: [姓名/联系方式]

### 升级路径
- **一级响应**: 系统管理员（30分钟内）
- **二级响应**: 开发团队（2小时内）
- **三级响应**: 业务负责人（4小时内）

## 版本信息

### 当前版本
- **系统版本**: MAREF v1.0
- **部署日期**: 2026年4月16日
- **基线版本**: 基于2026年4月15日24小时监控数据
- **配置版本**: production_config.py v1.0

### 更新记录
| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-16 | v1.0 | 初始生产部署 |
| 2026-04-15 | v0.9 | 完成24小时稳定性测试 |
| 2026-04-14 | v0.8 | 完成生产环境验证 |

---

**文档版本**: v1.0  
**创建日期**: 2026年4月16日  
**更新日期**: 2026年4月16日  
**负责人**: MAREF运维团队  
**状态**: 正式发布