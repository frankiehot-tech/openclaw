#!/usr/bin/env python3
"""
MAREF生产环境配置
"""

# 数据库配置
DATABASE_CONFIG = {
    "path": "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db",
    "performance_mode": True,
    "max_connections": 10,
    "cache_size": 1000,
}

# 内存管理器配置
MEMORY_MANAGER_CONFIG = {
    "memory_dir": "/Volumes/1TB-M2/openclaw/memory/maref",
    "entry_ttl_days": 30,
    "max_entries_per_type": 10000,
    "auto_cleanup": True,
}

# 监控器配置
MONITOR_CONFIG = {
    "collection_interval_seconds": 60,
    "metrics_retention_days": 7,
    "alert_check_interval": 300,
}

# 预警系统配置
ALERT_CONFIG = {
    "red_rules": [
        "H_C_OUT_OF_RANGE",  # 控制熵异常
        "GRAY_CODE_VIOLATION_HIGH",  # 格雷编码违规率高
        "STATE_TRANSITION_BROKEN",  # 状态转换中断
        "SYSTEM_CRASH",  # 系统崩溃
        "DATABASE_CORRUPTION",  # 数据库损坏
    ],
    "yellow_rules": [
        "LEARNER_STAGNATION",  # 学习停滞
        "SYSTEM_RESOURCE_WARNING",  # 系统资源警告
        "AGENT_HEALTH_DEGRADATION",  # 智能体健康度下降
        "PERFORMANCE_DEGRADATION",  # 性能下降
        "MEMORY_USAGE_HIGH",  # 内存使用率高
    ],
    # 基于实际数据的阈值调整
    "thresholds": {
        # 系统资源阈值（基于基线）
        "cpu_usage_yellow": 60.0,  # 警告阈值
        "cpu_usage_red": 80.0,  # 紧急阈值
        "memory_usage_yellow": 70.0,
        "memory_usage_red": 85.0,
        "disk_usage_yellow": 80.0,
        "disk_usage_red": 90.0,
        # MAREF指标阈值
        "control_entropy_yellow": 0.5,  # 控制熵警告阈值
        "control_entropy_red": 1.0,  # 控制熵紧急阈值
        "gray_code_violation_yellow": 0.05,  # 5%违规率警告
        "gray_code_violation_red": 0.10,  # 10%违规率紧急
        # 智能体健康度阈值
        "agent_health_yellow": 0.70,  # 健康度警告
        "agent_health_red": 0.60,  # 健康度紧急
        "agent_response_time_yellow": 10.0,  # 响应时间警告(ms)
        "agent_response_time_red": 20.0,  # 响应时间紧急(ms)
        # 数据库性能阈值
        "db_query_time_yellow": 15.0,  # 查询时间警告(ms)
        "db_query_time_red": 30.0,  # 查询时间紧急(ms)
        "db_connection_failures_yellow": 5,  # 连接失败警告
        "db_connection_failures_red": 10,  # 连接失败紧急
    },
    # 通知配置
    "notification_channels": ["log", "email", "webhook"],
    "notification_settings": {
        "email_recipients": ["devops@example.com", "oncall@example.com"],
        "webhook_url": "https://alerts.example.com/hook",
        "repeat_interval_minutes": 30,  # 重复告警间隔
    },
    # 告警持续时间配置
    "min_duration_seconds": 60,  # 最短持续时间
    "cooldown_period_seconds": 300,  # 冷却时间
    "max_alerts_per_hour": 10,  # 每小时最大告警数
}

# 智能体配置
AGENT_CONFIG = {
    "guardian_safety_constraints": 5,
    "communicator_channels": 3,
    "learner_tasks": 3,
    "explorer_discoveries": 4,
    "complementary_pair_enabled": True,
}

# 性能阈值配置（基于24小时监控基线）
PERFORMANCE_THRESHOLDS = {
    "state_transition_time_ms": 0.5,
    "agent_decision_time_ms": 5,
    "database_query_time_ms": 10,
    "memory_usage_percent": 70,  # 基于基线：最大76.4%，警告阈值70%
    "cpu_usage_percent": 60,  # 基于基线：最大41.7%，警告阈值60%
    "disk_usage_percent": 80,  # 基于基线：最大59.1%，警告阈值80%
    "throughput_state_transitions": 100,
    # 新增基于基线的阈值
    "control_entropy_threshold": 0.5,
    "gray_code_violation_threshold": 0.05,
    "agent_health_threshold": 0.70,
    "agent_response_time_threshold_ms": 10.0,
}

# 安全配置
SECURITY_CONFIG = {
    "enable_audit_log": True,
    "audit_events": ["state_transition", "agent_decision", "system_config_change", "data_access"],
    "audit_retention_days": 365,
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "file": "/Volumes/1TB-M2/openclaw/scripts/clawra/logs/maref_production.log",
    "max_size_mb": 100,
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
