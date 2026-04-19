#!/usr/bin/env python3
"""
成本监控Web仪表板

提供可视化界面展示迁移监控指标：
1. 实时成本节省数据
2. 质量一致性指标
3. 迁移进度和趋势
4. 异常检测和告警

使用Flask作为Web框架，Chart.js作为前端图表库。
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 添加mini-agent到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, jsonify, render_template, request, send_from_directory

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("警告: Flask未安装，无法启动Web仪表板")
    print("安装命令: pip install flask")

try:
    from agent.core.cost_tracker import CostTracker
    from agent.core.migration_monitor import MigrationMetrics, MigrationMonitor

    MIGRATION_MONITOR_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入迁移监控器: {e}")
    MIGRATION_MONITOR_AVAILABLE = False

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "web", "static"),
    template_folder=os.path.join(os.path.dirname(__file__), "web", "templates"),
)

# 全局监控器实例
migration_monitor = None
cost_tracker = None


def init_monitors():
    """初始化监控器实例"""
    global migration_monitor, cost_tracker

    if not MIGRATION_MONITOR_AVAILABLE:
        return False

    try:
        # 初始化迁移监控器
        db_path = os.path.join(os.path.dirname(__file__), "data", "cost_tracking.db")
        migration_monitor = MigrationMonitor(db_path=db_path, check_interval_minutes=15)

        # 初始化成本跟踪器
        cost_tracker = CostTracker(storage_backend="sqlite", config={"db_path": db_path})

        logger.info("监控器初始化成功")
        return True
    except Exception as e:
        logger.error(f"监控器初始化失败: {e}")
        return False


@app.route("/")
def index():
    """主仪表板页面"""
    return render_template("index.html")


@app.route("/api/health")
def health_check():
    """健康检查端点"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "monitors_available": MIGRATION_MONITOR_AVAILABLE,
            "migration_monitor_initialized": migration_monitor is not None,
            "cost_tracker_initialized": cost_tracker is not None,
        }
    )


@app.route("/api/migration/current_metrics")
def get_current_migration_metrics():
    """获取当前迁移指标"""
    if not migration_monitor:
        return jsonify({"error": "迁移监控器未初始化"}), 500

    try:
        # 收集当前指标
        metrics = migration_monitor.collect_migration_metrics(
            experiment_id="coding_plan_deepseek_coder_ab", lookback_hours=24
        )

        if metrics:
            # 转换为字典
            metrics_dict = {
                "timestamp": metrics.timestamp.isoformat(),
                "experiment_id": metrics.experiment_id,
                "phase_number": metrics.phase_number,
                # 请求统计
                "total_requests": metrics.total_requests,
                "dashscope_requests": metrics.dashscope_requests,
                "deepseek_requests": metrics.deepseek_requests,
                # 成本数据
                "dashscope_cost": metrics.dashscope_cost,
                "deepseek_cost": metrics.deepseek_cost,
                "cost_savings_percent": metrics.cost_savings_percent,
                # 质量数据
                "dashscope_quality_avg": metrics.dashscope_quality_avg,
                "deepseek_quality_avg": metrics.deepseek_quality_avg,
                "quality_consistency": metrics.quality_consistency,
                # 错误率
                "dashscope_error_rate": metrics.dashscope_error_rate,
                "deepseek_error_rate": metrics.deepseek_error_rate,
                "error_rate_diff": metrics.error_rate_diff,
                # 响应时间
                "dashscope_response_time_avg": metrics.dashscope_response_time_avg,
                "deepseek_response_time_avg": metrics.deepseek_response_time_avg,
                "response_time_diff_percent": metrics.response_time_diff_percent,
                # 监控窗口
                "monitoring_window_minutes": metrics.monitoring_window_minutes,
            }
            return jsonify(metrics_dict)
        else:
            return jsonify({"error": "无法收集迁移指标"}), 500

    except Exception as e:
        logger.error(f"获取迁移指标失败: {e}")
        return jsonify({"error": str(e)}), 500


def query_migration_history_from_db(hours_back=24, interval_hours=1):
    """从数据库查询迁移历史指标

    Args:
        hours_back: 回溯小时数
        interval_hours: 时间间隔小时数

    Returns:
        历史数据列表
    """
    if not migration_monitor:
        return []

    try:
        import sqlite3
        from datetime import datetime, timedelta

        db_path = migration_monitor.db_path
        if not db_path or not os.path.exists(db_path):
            logger.warning(f"数据库文件不存在: {db_path}")
            return []

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        # 按时间窗口查询实验记录
        # 我们将按小时分组，计算每个时间窗口的指标
        history_data = []

        # 简单查询：获取所有实验记录并按时间排序
        # 然后按时间窗口分组
        cursor.execute(
            """
            SELECT
                recorded_at,
                group_name,
                quality_score,
                execution_time,
                request_id,
                cost_record_id
            FROM experiment_records
            WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
              AND recorded_at >= ?
            ORDER BY recorded_at DESC
        """,
            (start_time.isoformat(),),
        )

        exp_records = cursor.fetchall()

        if not exp_records:
            conn.close()
            return []

        # 分组映射
        group_to_provider = {
            "original": "dashscope",
            "migrated": "deepseek",
            "control": "dashscope",
            "treatment": "deepseek",
        }

        # 按小时分组
        hourly_data = {}

        for record in exp_records:
            recorded_at = record["recorded_at"]
            if not recorded_at:
                continue

            try:
                record_time = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                hour_key = record_time.strftime("%Y-%m-%d %H:00")

                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {
                        "timestamp": record_time.replace(minute=0, second=0, microsecond=0),
                        "dashscope": {"requests": 0, "cost": 0.0, "quality_sum": 0.0, "errors": 0},
                        "deepseek": {"requests": 0, "cost": 0.0, "quality_sum": 0.0, "errors": 0},
                    }

                group_name = record["group_name"]
                provider = group_to_provider.get(group_name)
                if not provider or provider not in hourly_data[hour_key]:
                    continue

                # 增加请求计数
                hourly_data[hour_key][provider]["requests"] += 1

                # 质量评分
                quality = record["quality_score"] or 0.0
                hourly_data[hour_key][provider]["quality_sum"] += quality
                if quality <= 0:
                    hourly_data[hour_key][provider]["errors"] += 1

                # 成本数据 - 尝试查询关联的成本记录
                request_id = record["request_id"]
                cost_record_id = record["cost_record_id"]
                cost = 0.0

                if cost_record_id:
                    cost_query = "SELECT estimated_cost FROM cost_records WHERE id = ?"
                    cursor.execute(cost_query, (cost_record_id,))
                    cost_row = cursor.fetchone()
                    if cost_row:
                        cost = cost_row["estimated_cost"] or 0.0
                elif request_id:
                    # 尝试通过request_id查找成本记录
                    cost_query = "SELECT estimated_cost FROM cost_records WHERE request_id = ?"
                    cursor.execute(cost_query, (request_id,))
                    cost_row = cursor.fetchone()
                    if cost_row:
                        cost = cost_row["estimated_cost"] or 0.0

                hourly_data[hour_key][provider]["cost"] += cost

            except Exception as e:
                logger.debug(f"处理记录时出错: {e}")
                continue

        conn.close()

        # 转换为历史数据格式
        for hour_key, data in sorted(hourly_data.items(), reverse=True):
            ds = data["dashscope"]
            dk = data["deepseek"]

            # 计算指标
            ds_requests = ds["requests"]
            dk_requests = dk["requests"]
            total_requests = ds_requests + dk_requests

            # 成本节省
            cost_savings = 0.0
            if ds_requests > 0 and dk_requests > 0:
                ds_avg_cost = ds["cost"] / ds_requests if ds["cost"] > 0 else 0.0
                dk_avg_cost = dk["cost"] / dk_requests if dk["cost"] > 0 else 0.0
                if ds_avg_cost > 0:
                    cost_savings = (ds_avg_cost - dk_avg_cost) / ds_avg_cost * 100

            # 质量平均值
            ds_quality_avg = ds["quality_sum"] / ds_requests if ds_requests > 0 else 0.0
            dk_quality_avg = dk["quality_sum"] / dk_requests if dk_requests > 0 else 0.0

            # 质量一致性
            quality_consistency = dk_quality_avg / ds_quality_avg if ds_quality_avg > 0 else 1.0

            history_data.append(
                {
                    "timestamp": data["timestamp"].isoformat(),
                    "cost_savings_percent": cost_savings,
                    "quality_consistency": quality_consistency,
                    "dashscope_cost": ds["cost"],
                    "deepseek_cost": dk["cost"],
                    "dashscope_requests": ds_requests,
                    "deepseek_requests": dk_requests,
                    "dashscope_quality_avg": ds_quality_avg,
                    "deepseek_quality_avg": dk_quality_avg,
                }
            )

        # 返回最近的数据点（最多50个）
        return history_data[:50]

    except Exception as e:
        logger.error(f"查询迁移历史失败: {e}")
        return []


@app.route("/api/migration/history")
def get_migration_history():
    """获取迁移历史指标"""
    if not migration_monitor:
        return jsonify({"error": "迁移监控器未初始化"}), 500

    try:
        # 从数据库查询历史数据
        history_data = query_migration_history_from_db(hours_back=48, interval_hours=1)

        return jsonify({"history": history_data})
    except Exception as e:
        logger.error(f"获取迁移历史失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/cost/trends")
def get_cost_trends():
    """获取成本趋势数据"""
    if not cost_tracker:
        return jsonify({"error": "成本跟踪器未初始化"}), 500

    try:
        # 获取最近7天的成本数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # 这里需要实现实际的数据查询
        # 暂时返回模拟数据
        trends = {
            "daily_costs": [
                {
                    "date": (end_date - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "dashscope_cost": 0.5 + i * 0.1,
                    "deepseek_cost": 0.2 + i * 0.05,
                }
                for i in range(7, 0, -1)
            ],
            "provider_breakdown": [
                {"provider": "dashscope", "cost": 3.5, "requests": 100},
                {"provider": "deepseek", "cost": 1.8, "requests": 80},
            ],
        }

        return jsonify(trends)
    except Exception as e:
        logger.error(f"获取成本趋势失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts")
def get_alerts():
    """获取迁移告警"""
    if not migration_monitor:
        return jsonify({"error": "迁移监控器未初始化"}), 500

    try:
        alerts = []
        if hasattr(migration_monitor, "alerts") and migration_monitor.alerts:
            for alert in migration_monitor.alerts[-10:]:  # 最近10个告警
                alerts.append(
                    {
                        "alert_id": alert.alert_id,
                        "level": (
                            alert.level.value if hasattr(alert.level, "value") else str(alert.level)
                        ),
                        "metric": (
                            alert.metric.value
                            if hasattr(alert.metric, "value")
                            else str(alert.metric)
                        ),
                        "message": alert.message,
                        "value": alert.value,
                        "threshold": alert.threshold,
                        "timestamp": alert.timestamp.isoformat(),
                        "resolved": alert.resolved,
                    }
                )

        return jsonify({"alerts": alerts})
    except Exception as e:
        logger.error(f"获取告警失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/experiments")
def get_experiments():
    """获取实验列表"""
    try:
        experiments = [
            {
                "id": "coding_plan_deepseek_coder_ab",
                "name": "DeepSeek Coder迁移实验",
                "description": "将代码规划任务从DashScope迁移到DeepSeek Coder",
                "start_date": "2026-04-10",
                "status": "running",
                "current_phase": 1,
                "total_phases": 4,
            }
        ]
        return jsonify({"experiments": experiments})
    except Exception as e:
        logger.error(f"获取实验列表失败: {e}")
        return jsonify({"error": str(e)}), 500


# 创建Web目录结构
def create_web_directories():
    """创建Web目录结构"""
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    static_dir = os.path.join(web_dir, "static")
    templates_dir = os.path.join(web_dir, "templates")

    for directory in [web_dir, static_dir, templates_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")


def create_index_template():
    """创建HTML模板文件"""
    templates_dir = os.path.join(os.path.dirname(__file__), "web", "templates")
    index_path = os.path.join(templates_dir, "index.html")

    if not os.path.exists(index_path):
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>成本监控仪表板 - 迁移监控系统</title>

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>
        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
            border-radius: 0 0 20px 20px;
        }

        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }

        .metric-positive {
            color: #28a745;
        }

        .metric-negative {
            color: #dc3545;
        }

        .metric-label {
            color: #6c757d;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .alert-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .alert-critical {
            border-left: 5px solid #dc3545;
        }

        .alert-warning {
            border-left: 5px solid #ffc107;
        }

        .alert-info {
            border-left: 5px solid #17a2b8;
        }

        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 0.5rem 1.5rem;
            border-radius: 25px;
            font-weight: bold;
        }

        .provider-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }

        .dashscope-badge {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        .deepseek-badge {
            background-color: #e8f5e9;
            color: #388e3c;
        }
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg navbar-dark dashboard-header">
        <div class="container">
            <a class="navbar-brand" href="#">
                <h2>📊 成本监控仪表板</h2>
            </a>
            <div class="navbar-text">
                <span id="current-time"></span>
                <button class="btn btn-light ms-3" onclick="refreshDashboard()">🔄 刷新数据</button>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- 顶部指标卡片 -->
        <div class="row">
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-label">成本节省</div>
                    <div id="cost-savings-value" class="metric-value metric-positive">0%</div>
                    <div class="metric-details">
                        <small>自迁移开始</small>
                    </div>
                </div>
            </div>

            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-label">质量一致性</div>
                    <div id="quality-consistency-value" class="metric-value">0.00</div>
                    <div class="metric-details">
                        <small>DeepSeek/DashScope</small>
                    </div>
                </div>
            </div>

            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-label">总请求数</div>
                    <div id="total-requests-value" class="metric-value">0</div>
                    <div class="metric-details">
                        <small>24小时内</small>
                    </div>
                </div>
            </div>

            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-label">迁移进度</div>
                    <div id="migration-progress-value" class="metric-value">0%</div>
                    <div class="metric-details">
                        <small>阶段 1/4</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- 图表行 -->
        <div class="row">
            <div class="col-lg-8">
                <div class="chart-container">
                    <h5>成本节省趋势</h5>
                    <canvas id="costSavingsChart"></canvas>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="chart-container">
                    <h5>请求分布</h5>
                    <canvas id="requestDistributionChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 详细数据行 -->
        <div class="row">
            <div class="col-md-6">
                <div class="chart-container">
                    <h5>成本对比</h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="metric-card text-center">
                                <div class="metric-label">DashScope成本</div>
                                <div id="dashscope-cost-value" class="metric-value">$0.00</div>
                                <div class="metric-details">
                                    <span id="dashscope-requests-value">0 请求</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="metric-card text-center">
                                <div class="metric-label">DeepSeek成本</div>
                                <div id="deepseek-cost-value" class="metric-value">$0.00</div>
                                <div class="metric-details">
                                    <span id="deepseek-requests-value">0 请求</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <canvas id="costComparisonChart" height="150"></canvas>
                </div>
            </div>

            <div class="col-md-6">
                <div class="chart-container">
                    <h5>质量评分对比</h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="metric-card text-center">
                                <div class="metric-label">DashScope质量</div>
                                <div id="dashscope-quality-value" class="metric-value">0.00</div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="metric-card text-center">
                                <div class="metric-label">DeepSeek质量</div>
                                <div id="deepseek-quality-value" class="metric-value">0.00</div>
                            </div>
                        </div>
                    </div>
                    <canvas id="qualityComparisonChart" height="150"></canvas>
                </div>
            </div>
        </div>

        <!-- 告警行 -->
        <div class="row">
            <div class="col-12">
                <div class="alert-card">
                    <h5>系统告警</h5>
                    <div id="alerts-container">
                        <div class="text-center text-muted py-4">
                            正在加载告警...
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 实验信息 -->
        <div class="row">
            <div class="col-12">
                <div class="chart-container">
                    <h5>实验信息</h5>
                    <div id="experiment-info">
                        <p>正在加载实验信息...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript -->
    <script>
        // 全局变量
        let costSavingsChart = null;
        let requestDistributionChart = null;
        let costComparisonChart = null;
        let qualityComparisonChart = null;

        // 更新当前时间
        function updateCurrentTime() {
            const now = new Date();
            const timeStr = now.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            document.getElementById('current-time').textContent = `最后更新: ${timeStr}`;
        }

        // 刷新仪表板数据
        async function refreshDashboard() {
            try {
                await Promise.all([
                    loadCurrentMetrics(),
                    loadHistoryData(),
                    loadAlerts(),
                    loadExperimentInfo()
                ]);
                updateCurrentTime();
            } catch (error) {
                console.error('刷新数据失败:', error);
                alert('刷新数据失败: ' + error.message);
            }
        }

        // 加载当前指标
        async function loadCurrentMetrics() {
            try {
                const response = await fetch('/api/migration/current_metrics');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();

                // 更新指标卡片
                document.getElementById('cost-savings-value').textContent =
                    `${data.cost_savings_percent?.toFixed(1) || 0}%`;

                document.getElementById('quality-consistency-value').textContent =
                    data.quality_consistency?.toFixed(2) || '0.00';

                document.getElementById('total-requests-value').textContent =
                    data.total_requests || 0;

                // 设置迁移进度（基于请求比例）
                const total = data.total_requests || 1;
                const deepseekPct = data.deepseek_requests ? (data.deepseek_requests / total * 100).toFixed(0) : 0;
                document.getElementById('migration-progress-value').textContent =
                    `${deepseekPct}%`;

                // 成本数据
                document.getElementById('dashscope-cost-value').textContent =
                    `$${(data.dashscope_cost || 0).toFixed(4)}`;
                document.getElementById('deepseek-cost-value').textContent =
                    `$${(data.deepseek_cost || 0).toFixed(4)}`;

                document.getElementById('dashscope-requests-value').textContent =
                    `${data.dashscope_requests || 0} 请求`;
                document.getElementById('deepseek-requests-value').textContent =
                    `${data.deepseek_requests || 0} 请求`;

                // 质量数据
                document.getElementById('dashscope-quality-value').textContent =
                    (data.dashscope_quality_avg || 0).toFixed(2);
                document.getElementById('deepseek-quality-value').textContent =
                    (data.deepseek_quality_avg || 0).toFixed(2);

                // 更新成本对比图表
                updateCostComparisonChart(data);

                // 更新质量对比图表
                updateQualityComparisonChart(data);

                // 更新请求分布图表
                updateRequestDistributionChart(data);

            } catch (error) {
                console.error('加载当前指标失败:', error);
            }
        }

        // 加载历史数据
        async function loadHistoryData() {
            try {
                const response = await fetch('/api/migration/history');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();

                if (data.history && data.history.length > 0) {
                    updateCostSavingsChart(data.history);
                }
            } catch (error) {
                console.error('加载历史数据失败:', error);
            }
        }

        // 加载告警
        async function loadAlerts() {
            try {
                const response = await fetch('/api/alerts');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();
                updateAlertsDisplay(data.alerts || []);
            } catch (error) {
                console.error('加载告警失败:', error);
            }
        }

        // 加载实验信息
        async function loadExperimentInfo() {
            try {
                const response = await fetch('/api/experiments');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();
                updateExperimentInfo(data.experiments || []);
            } catch (error) {
                console.error('加载实验信息失败:', error);
            }
        }

        // 更新成本节省趋势图表
        function updateCostSavingsChart(historyData) {
            const ctx = document.getElementById('costSavingsChart').getContext('2d');

            const labels = historyData.map(item => {
                const date = new Date(item.timestamp);
                return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
            });

            const costSavings = historyData.map(item => item.cost_savings_percent || 0);

            if (costSavingsChart) {
                costSavingsChart.destroy();
            }

            costSavingsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '成本节省 %',
                        data: costSavings,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: '成本节省趋势'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '节省百分比 (%)'
                            }
                        }
                    }
                }
            });
        }

        // 更新请求分布图表
        function updateRequestDistributionChart(data) {
            const ctx = document.getElementById('requestDistributionChart').getContext('2d');

            if (requestDistributionChart) {
                requestDistributionChart.destroy();
            }

            requestDistributionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['DashScope', 'DeepSeek'],
                    datasets: [{
                        data: [data.dashscope_requests || 0, data.deepseek_requests || 0],
                        backgroundColor: [
                            'rgba(25, 118, 210, 0.7)',
                            'rgba(56, 142, 60, 0.7)'
                        ],
                        borderColor: [
                            'rgb(25, 118, 210)',
                            'rgb(56, 142, 60)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: '请求分布'
                        }
                    }
                }
            });
        }

        // 更新成本对比图表
        function updateCostComparisonChart(data) {
            const ctx = document.getElementById('costComparisonChart').getContext('2d');

            if (costComparisonChart) {
                costComparisonChart.destroy();
            }

            costComparisonChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['DashScope', 'DeepSeek'],
                    datasets: [{
                        label: '成本 ($)',
                        data: [data.dashscope_cost || 0, data.deepseek_cost || 0],
                        backgroundColor: [
                            'rgba(25, 118, 210, 0.7)',
                            'rgba(56, 142, 60, 0.7)'
                        ],
                        borderColor: [
                            'rgb(25, 118, 210)',
                            'rgb(56, 142, 60)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '成本 ($)'
                            }
                        }
                    }
                }
            });
        }

        // 更新质量对比图表
        function updateQualityComparisonChart(data) {
            const ctx = document.getElementById('qualityComparisonChart').getContext('2d');

            if (qualityComparisonChart) {
                qualityComparisonChart.destroy();
            }

            qualityComparisonChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['DashScope', 'DeepSeek'],
                    datasets: [{
                        label: '质量评分',
                        data: [data.dashscope_quality_avg || 0, data.deepseek_quality_avg || 0],
                        backgroundColor: [
                            'rgba(25, 118, 210, 0.7)',
                            'rgba(56, 142, 60, 0.7)'
                        ],
                        borderColor: [
                            'rgb(25, 118, 210)',
                            'rgb(56, 142, 60)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1.0,
                            title: {
                                display: true,
                                text: '质量评分'
                            }
                        }
                    }
                }
            });
        }

        // 更新告警显示
        function updateAlertsDisplay(alerts) {
            const container = document.getElementById('alerts-container');

            if (alerts.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-muted py-4">
                        <div class="mb-2">✅ 一切正常</div>
                        <small>没有未解决的告警</small>
                    </div>
                `;
                return;
            }

            let alertsHtml = '';
            alerts.forEach(alert => {
                let alertClass = '';
                let icon = '';

                switch (alert.level) {
                    case 'critical':
                        alertClass = 'alert-critical';
                        icon = '🔴';
                        break;
                    case 'warning':
                        alertClass = 'alert-warning';
                        icon = '🟡';
                        break;
                    default:
                        alertClass = 'alert-info';
                        icon = '🔵';
                }

                const time = new Date(alert.timestamp).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                });

                alertsHtml += `
                    <div class="alert ${alertClass} mb-2 p-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong>${icon} ${alert.metric}</strong>
                                <div class="mt-1">${alert.message}</div>
                                <small class="text-muted">${time} - 值: ${alert.value.toFixed(2)}</small>
                            </div>
                            <div>
                                <span class="badge ${alert.resolved ? 'bg-success' : 'bg-danger'}">
                                    ${alert.resolved ? '已解决' : '未解决'}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = alertsHtml;
        }

        // 更新实验信息
        function updateExperimentInfo(experiments) {
            const container = document.getElementById('experiment-info');

            if (experiments.length === 0) {
                container.innerHTML = '<p class="text-muted">没有活跃的实验</p>';
                return;
            }

            let html = '';
            experiments.forEach(exp => {
                html += `
                    <div class="card mb-3">
                        <div class="card-body">
                            <h6 class="card-title">${exp.name}</h6>
                            <p class="card-text">${exp.description}</p>
                            <div class="row">
                                <div class="col-md-3">
                                    <small class="text-muted">ID</small>
                                    <div>${exp.id}</div>
                                </div>
                                <div class="col-md-3">
                                    <small class="text-muted">状态</small>
                                    <div>
                                        <span class="badge ${exp.status === 'running' ? 'bg-success' : 'bg-warning'}">
                                            ${exp.status === 'running' ? '运行中' : '已暂停'}
                                        </span>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <small class="text-muted">阶段</small>
                                    <div>${exp.current_phase}/${exp.total_phases}</div>
                                </div>
                                <div class="col-md-3">
                                    <small class="text-muted">开始时间</small>
                                    <div>${exp.start_date}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        // 初始化仪表板
        document.addEventListener('DOMContentLoaded', function() {
            updateCurrentTime();
            refreshDashboard();

            // 每30秒自动刷新
            setInterval(refreshDashboard, 30000);
        });
    </script>
</body>
</html>
"""

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"创建HTML模板: {index_path}")
        return True


def main():
    """主函数"""
    if not FLASK_AVAILABLE:
        print("错误: Flask未安装，无法启动Web仪表板")
        print("请运行: pip install flask")
        sys.exit(1)

    if not MIGRATION_MONITOR_AVAILABLE:
        print("警告: 迁移监控器组件不可用，仪表板将以模拟模式运行")

    # 创建Web目录结构
    create_web_directories()
    create_index_template()

    # 初始化监控器
    init_monitors()

    # 启动Flask应用
    host = os.environ.get("COST_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("COST_DASHBOARD_PORT", 5001))

    print(f"🚀 启动成本监控仪表板...")
    print(f"📊 访问地址: http://{host}:{port}")
    print(f"🔍 健康检查: http://{host}:{port}/api/health")
    print(f"📈 当前指标: http://{host}:{port}/api/migration/current_metrics")
    print("🔄 按 Ctrl+C 停止服务器")

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
