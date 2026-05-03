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
        "availability": 1.0,
    },
    # 系统资源基线（基于实际监控数据）
    "system_resources": {
        "cpu_usage": {
            "average": 1.4,  # 平均使用率 %
            "minimum": 0.0,  # 最小值 %
            "maximum": 41.7,  # 最大值 %
            "standard_deviation": 1.2,  # 估算标准差
        },
        "memory_usage": {
            "average": 58.2,  # 平均使用率 %
            "minimum": 53.1,  # 最小值 %
            "maximum": 76.4,  # 最大值 %
            "standard_deviation": 2.8,  # 估算标准差
        },
        "disk_usage": {
            "average": 57.5,  # 平均使用率 %
            "minimum": 55.8,  # 最小值 %
            "maximum": 59.1,  # 最大值 %
            "standard_deviation": 0.5,  # 估算标准差
        },
    },
    # MAREF指标基线
    "maref_metrics": {
        "control_entropy_h_c": {"average": 0.0, "minimum": 0.0, "maximum": 0.0},
        "gray_code_compliance_rate": 1.0,  # 100%合规
        "state_stability": {"changes_per_24h": 1, "avg_state_duration_minutes": 1440.6},
    },
    # 智能体健康度基线
    "agent_health": {
        "guardian": 0.80,
        "communicator": 0.80,
        "learner": 0.80,
        "explorer": 0.80,
        "all_agents_average": 0.80,
    },
    # 性能阈值（基于基线+20%容差）
    "performance_thresholds": {
        "cpu_usage_warning": 60.0,  # 基线41.7 + 20%
        "cpu_usage_critical": 80.0,
        "memory_usage_warning": 70.0,  # 基线58.2 + 20%
        "memory_usage_critical": 85.0,
        "agent_health_warning": 0.70,  # 基线0.80 - 10%
        "agent_health_critical": 0.60,
    },
}
