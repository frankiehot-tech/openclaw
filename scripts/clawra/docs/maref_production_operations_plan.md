# MAREF生产运维计划

基于24小时长期稳定性验证结果，制定以下生产运维任务计划。

**验证结果摘要**:
- ✅ 24小时288次检查，100%可用性
- ✅ 零错误运行，系统可靠性极高
- ✅ 所有性能指标优于配置阈值
- ✅ 系统已准备好投入正式生产

## 任务1: 建立定期监控计划

### 目标
建立每周一次的24小时深度监控，持续验证系统稳定性。

### 实施步骤

#### 1.1 创建定期监控脚本
创建 `run_weekly_stability_monitor.sh` 脚本：
```bash
#!/bin/bash
# 每周执行一次24小时稳定性监控

# 参数配置
MONITOR_SCRIPT="monitor_long_term_stability.py"
HOURS=24
INTERVAL=300  # 5分钟
LOG_DIR="logs/weekly_monitor"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/weekly_monitor_${TIMESTAMP}.log"
REPORT_FILE="$LOG_DIR/weekly_report_${TIMESTAMP}.json"

# 执行监控
echo "=== 开始每周稳定性监控 ===" | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "时长: $HOURS 小时" | tee -a "$LOG_FILE"
echo "间隔: $INTERVAL 秒" | tee -a "$LOG_FILE"

# 启动监控
python3 "$MONITOR_SCRIPT" --hours "$HOURS" --interval "$INTERVAL" >> "$LOG_FILE" 2>&1

# 监控结束后分析数据
if [ $? -eq 0 ]; then
    echo "监控完成，开始分析数据..." | tee -a "$LOG_FILE"
    
    # 查找最新的监控完成文件
    LATEST_COMPLETE=$(ls -t logs/long_term_monitor_complete_*.json | head -1)
    
    if [ -f "$LATEST_COMPLETE" ]; then
        # 使用分析脚本
        python3 analyze_long_term_monitor.py --input "$LATEST_COMPLETE" --output "$REPORT_FILE"
        echo "分析报告已生成: $REPORT_FILE" | tee -a "$LOG_FILE"
    else
        echo "警告: 未找到监控完成文件" | tee -a "$LOG_FILE"
    fi
else
    echo "监控执行失败，请检查日志: $LOG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

echo "=== 每周稳定性监控完成 ===" | tee -a "$LOG_FILE"
```

#### 1.2 创建cron定时任务
```bash
# 编辑crontab
crontab -e

# 添加以下行（每周一凌晨2点执行）
0 2 * * 1 /Volumes/1TB-M2/openclaw/scripts/clawra/run_weekly_stability_monitor.sh
```

#### 1.3 监控结果管理
创建监控结果归档策略：
- 保留最近4次周度监控报告
- 压缩30天前的监控日志
- 90天后自动清理

## 任务2: 建立性能基线

### 目标
基于24小时监控数据，建立系统性能基准线。

### 实施步骤

#### 2.1 创建性能基线配置文件
创建 `config/performance_baseline.py`：
```python
"""
性能基线配置 - 基于24小时监控数据建立
"""

PERFORMANCE_BASELINE = {
    # 基于24小时监控数据的实际性能
    "24_hour_monitoring": {
        "start_time": "2026-04-15T08:30:54.114552",
        "end_time": "2026-04-16T08:30:54.114552",
        "total_checks": 288,
        "error_rate": 0.0,
        "availability": 1.0
    },
    
    # 系统资源基线
    "system_resources": {
        "cpu_usage": {
            "average": 1.4,      # 平均使用率 %
            "minimum": 0.0,      # 最小值 %
            "maximum": 41.7,     # 最大值 %
            "standard_deviation": 1.2  # 标准差
        },
        "memory_usage": {
            "average": 58.2,     # 平均使用率 %
            "minimum": 53.1,     # 最小值 %
            "maximum": 76.4,     # 最大值 %
            "standard_deviation": 2.8
        },
        "disk_usage": {
            "average": 57.5,     # 平均使用率 %
            "minimum": 55.8,     # 最小值 %
            "maximum": 59.1,     # 最大值 %
            "standard_deviation": 0.5
        }
    },
    
    # MAREF指标基线
    "maref_metrics": {
        "control_entropy_h_c": {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0
        },
        "gray_code_compliance_rate": 1.0,  # 100%合规
        "state_stability": {
            "changes_per_24h": 1,
            "avg_state_duration_minutes": 1440.6
        }
    },
    
    # 智能体健康度基线
    "agent_health": {
        "guardian": 0.80,
        "communicator": 0.80,
        "learner": 0.80,
        "explorer": 0.80,
        "all_agents_average": 0.80
    },
    
    # 性能阈值（基于基线+20%容差）
    "performance_thresholds": {
        "cpu_usage_warning": 60.0,      # 基线41.7 + 20%
        "cpu_usage_critical": 80.0,
        "memory_usage_warning": 70.0,   # 基线58.2 + 20%
        "memory_usage_critical": 85.0,
        "agent_health_warning": 0.70,   # 基线0.80 - 10%
        "agent_health_critical": 0.60
    }
}
```

#### 2.2 创建基线验证脚本
创建 `validate_performance_baseline.py`：
```python
#!/usr/bin/env python3
"""
性能基线验证脚本
比较当前性能与基线数据
"""

import json
import sys
from datetime import datetime
from pathlib import Path

def load_baseline():
    """加载性能基线配置"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config.performance_baseline import PERFORMANCE_BASELINE
        return PERFORMANCE_BASELINE
    except ImportError:
        print("❌ 无法加载性能基线配置")
        return None

def validate_current_performance(baseline):
    """验证当前性能是否符合基线"""
    # 这里实现实际性能数据采集和比较
    # 返回验证结果和偏差报告
    pass

def main():
    baseline = load_baseline()
    if not baseline:
        return 1
    
    print("=== 性能基线验证 ===")
    print(f"基线时间范围: {baseline['24_hour_monitoring']['start_time']} 至 {baseline['24_hour_monitoring']['end_time']}")
    print(f"基线可用性: {baseline['24_hour_monitoring']['availability']*100:.1f}%")
    print(f"基线错误率: {baseline['24_hour_monitoring']['error_rate']*100:.2f}%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## 任务3: 优化告警规则

### 目标
基于实际运行数据，优化预警系统阈值和规则。

### 实施步骤

#### 3.1 分析监控数据调整阈值
基于24小时监控数据，优化 `config/production_config.py` 中的告警规则：

```python
# 更新ALERT_CONFIG
ALERT_CONFIG = {
    "red_rules": [
        "H_C_OUT_OF_RANGE",           # 控制熵异常
        "GRAY_CODE_VIOLATION_HIGH",   # 格雷编码违规率高
        "STATE_TRANSITION_BROKEN",    # 状态转换中断
        "SYSTEM_CRASH",               # 系统崩溃
        "DATABASE_CORRUPTION"         # 数据库损坏
    ],
    "yellow_rules": [
        "LEARNER_STAGNATION",         # 学习停滞
        "SYSTEM_RESOURCE_WARNING",    # 系统资源警告
        "AGENT_HEALTH_DEGRADATION",   # 智能体健康度下降
        "PERFORMANCE_DEGRADATION",    # 性能下降
        "MEMORY_USAGE_HIGH"           # 内存使用率高
    ],
    
    # 基于实际数据的阈值调整
    "thresholds": {
        # 系统资源阈值（基于基线）
        "cpu_usage_yellow": 60.0,     # 警告阈值
        "cpu_usage_red": 80.0,        # 紧急阈值
        "memory_usage_yellow": 70.0,
        "memory_usage_red": 85.0,
        "disk_usage_yellow": 80.0,
        "disk_usage_red": 90.0,
        
        # MAREF指标阈值
        "control_entropy_yellow": 0.5,  # 控制熵警告阈值
        "control_entropy_red": 1.0,     # 控制熵紧急阈值
        "gray_code_violation_yellow": 0.05,  # 5%违规率警告
        "gray_code_violation_red": 0.10,     # 10%违规率紧急
        
        # 智能体健康度阈值
        "agent_health_yellow": 0.70,     # 健康度警告
        "agent_health_red": 0.60,        # 健康度紧急
        "agent_response_time_yellow": 10.0,  # 响应时间警告(ms)
        "agent_response_time_red": 20.0,     # 响应时间紧急(ms)
        
        # 数据库性能阈值
        "db_query_time_yellow": 15.0,    # 查询时间警告(ms)
        "db_query_time_red": 30.0,       # 查询时间紧急(ms)
        "db_connection_failures_yellow": 5,  # 连接失败警告
        "db_connection_failures_red": 10     # 连接失败紧急
    },
    
    # 通知配置
    "notification_channels": ["log", "email", "webhook"],
    "notification_settings": {
        "email_recipients": ["devops@example.com", "oncall@example.com"],
        "webhook_url": "https://alerts.example.com/hook",
        "repeat_interval_minutes": 30  # 重复告警间隔
    },
    
    # 告警持续时间配置
    "min_duration_seconds": 60,      # 最短持续时间
    "cooldown_period_seconds": 300,  # 冷却时间
    "max_alerts_per_hour": 10        # 每小时最大告警数
}
```

#### 3.2 创建告警规则验证脚本
创建 `validate_alert_rules.py`：
```python
#!/usr/bin/env python3
"""
告警规则验证脚本
验证告警阈值设置是否合理
"""

def validate_alert_thresholds():
    """验证告警阈值设置"""
    # 验证阈值是否基于实际基线
    # 验证阈值之间的逻辑关系
    # 生成验证报告
    pass
```

## 任务4: 执行首次备份

### 目标
使用已验证的备份脚本，执行首次生产环境完整备份。

### 实施步骤

#### 4.1 执行首次完整备份
```bash
# 创建备份目录
mkdir -p ./backup/maref

# 执行首次备份
./backup_maref_production.sh \
    --mode daily \
    --backup-dir ./backup/maref \
    --verbose

# 验证备份完整性
sqlite3 ./backup/maref/maref_memory_*.db "PRAGMA integrity_check;"

# 检查备份元数据
cat ./backup/maref/backup_metadata.json | python3 -m json.tool
```

#### 4.2 创建备份验证脚本
创建 `verify_backup_integrity.py`：
```python
#!/usr/bin/env python3
"""
备份完整性验证脚本
"""

import sqlite3
import json
import os
from pathlib import Path

def verify_backup_integrity(backup_file):
    """验证备份文件完整性"""
    try:
        conn = sqlite3.connect(backup_file)
        cursor = conn.cursor()
        
        # 1. 检查完整性
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]
        
        # 2. 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # 3. 检查数据量
        cursor.execute("SELECT COUNT(*) FROM memory_entries;")
        entry_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "backup_file": backup_file,
            "integrity_check": integrity_result,
            "tables_found": len(tables),
            "required_tables": ["memory_entries", "sqlite_sequence"],
            "all_tables_present": all(tbl in tables for tbl in ["memory_entries", "sqlite_sequence"]),
            "entry_count": entry_count,
            "valid": integrity_result == "ok" and entry_count > 0
        }
        
    except Exception as e:
        return {
            "backup_file": backup_file,
            "error": str(e),
            "valid": False
        }

def main():
    # 查找最新的备份文件
    backup_dir = Path("./backup/maref")
    backup_files = list(backup_dir.glob("maref_memory_*.db"))
    
    if not backup_files:
        print("❌ 未找到备份文件")
        return 1
    
    # 验证每个备份文件
    for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
        result = verify_backup_integrity(str(backup_file))
        
        print(f"\n验证备份: {backup_file.name}")
        if result["valid"]:
            print(f"  ✅ 完整性检查: {result['integrity_check']}")
            print(f"  ✅ 表数量: {result['tables_found']}")
            print(f"  ✅ 内存条目数: {result['entry_count']}")
        else:
            print(f"  ❌ 验证失败: {result.get('error', '未知错误')}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

#### 4.3 创建自动化备份计划
```bash
# 编辑crontab添加每日备份
crontab -e

# 添加以下行（每日凌晨3点执行备份）
0 3 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode daily --backup-dir ./backup/maref

# 添加每周完整备份（周日凌晨2点）
0 2 * * 0 cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode weekly --backup-dir ./backup/maref

# 添加每月完整备份（每月1日凌晨1点）
0 1 1 * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode monthly --backup-dir ./backup/maref
```

## 实施优先级和时间表

| 任务 | 优先级 | 预计时间 | 负责人 |
|------|--------|----------|--------|
| 1. 执行首次备份 | 高 | 立即 | 运维团队 |
| 2. 建立性能基线 | 中 | 1天 | 性能团队 |
| 3. 优化告警规则 | 中 | 2天 | 监控团队 |
| 4. 建立定期监控 | 低 | 3天 | 运维团队 |

## 成功标准

1. ✅ 首次备份成功执行并验证
2. ✅ 性能基线配置文件创建完成
3. ✅ 告警规则基于实际数据优化
4. ✅ 定期监控脚本部署并测试
5. ✅ 所有cron任务配置完成

## 风险评估

1. **备份影响** - 备份期间可能短暂影响数据库性能
   - 缓解：在业务低峰期执行备份

2. **监控开销** - 每周24小时监控可能增加系统负载
   - 缓解：优化监控间隔，使用性能模式

3. **告警噪声** - 新告警规则可能产生误报
   - 缓解：设置合适的阈值和冷却时间

## 验收标准

1. 备份文件可通过完整性检查
2. 性能基线数据与实际监控数据匹配
3. 告警阈值通过验证脚本检查
4. 定期监控脚本可成功执行

---

**文档版本**: v1.0  
**创建日期**: 2026-04-16  
**创建人**: MAREF运维规划系统  
**审核人**: [待审核]  
**更新记录**:
- v1.0: 初始版本，基于24小时监控结果创建