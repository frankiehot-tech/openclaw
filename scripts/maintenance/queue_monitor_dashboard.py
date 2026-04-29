#!/usr/bin/env python3
"""
队列监控Web仪表板
提供实时队列状态、系统资源和告警信息的可视化界面
"""

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil
from flask import Flask, jsonify, render_template

# 尝试导入Flask，如果未安装则提示
try:
    from flask import Flask, jsonify, render_template

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask未安装，请运行: pip install flask")
    print("💡 将创建HTML文件作为替代")

app = Flask(__name__, static_folder="static", template_folder="templates")

# 监控数据存储
monitoring_data = {
    "queues": [],
    "system_resources": {},
    "alerts": [],
    "last_update": None,
    "history": [],
}

# 监控器实例
queue_monitor = None


def load_queue_monitor():
    """加载队列监控器"""
    global queue_monitor
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.queue_monitor import QueueMonitor

        queue_monitor = QueueMonitor()
        return True
    except Exception as e:
        print(f"⚠️  加载队列监控器失败: {e}")
        return False


def collect_monitoring_data():
    """收集监控数据"""
    if queue_monitor:
        try:
            status = queue_monitor.check_queue_status()

            # 更新监控数据
            monitoring_data["queues"] = []
            for queue_name, queue_info in status.get("queues", {}).items():
                if queue_name != "total_files":
                    monitoring_data["queues"].append(
                        {
                            "name": queue_name,
                            "status": queue_info.get("queue_status", "unknown"),
                            "pause_reason": queue_info.get("pause_reason", ""),
                            "tasks": {
                                "total": queue_info.get("total_tasks", 0),
                                "pending": queue_info.get("counts", {}).get("pending", 0),
                                "running": queue_info.get("counts", {}).get("running", 0),
                                "completed": queue_info.get("counts", {}).get("completed", 0),
                                "failed": queue_info.get("counts", {}).get("failed", 0),
                                "manual_hold": queue_info.get("counts", {}).get("manual_hold", 0),
                            },
                            "last_updated": queue_info.get("updated_at", ""),
                            "age_minutes": queue_info.get("age_minutes", 0),
                        }
                    )

            monitoring_data["system_resources"] = status.get("system_resources", {})
            monitoring_data["alerts"] = status.get("alerts", [])
            monitoring_data["last_update"] = datetime.now().isoformat()

            # 保留最近100条历史记录
            monitoring_data["history"].append(
                {
                    "timestamp": monitoring_data["last_update"],
                    "queues_count": len(monitoring_data["queues"]),
                    "alerts_count": len(monitoring_data["alerts"]),
                    "cpu_usage": monitoring_data["system_resources"].get("cpu_percent", 0),
                    "memory_usage": monitoring_data["system_resources"].get("memory_percent", 0),
                }
            )

            if len(monitoring_data["history"]) > 100:
                monitoring_data["history"] = monitoring_data["history"][-100:]

        except Exception as e:
            print(f"❌ 收集监控数据失败: {e}")
    else:
        # 如果没有队列监控器，使用模拟数据
        monitoring_data["queues"] = [
            {
                "name": "openhuman_aiplan_gene_management_20260405",
                "status": "running",
                "tasks": {
                    "total": 18,
                    "pending": 11,
                    "running": 1,
                    "completed": 3,
                    "failed": 0,
                    "manual_hold": 0,
                },
                "last_updated": datetime.now().isoformat(),
            },
            {
                "name": "openhuman_aiplan_plan_manual_20260328",
                "status": "running",
                "tasks": {
                    "total": 20,
                    "pending": 5,
                    "running": 1,
                    "completed": 20,
                    "failed": 0,
                    "manual_hold": 0,
                },
                "last_updated": datetime.now().isoformat(),
            },
        ]

        monitoring_data["system_resources"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
        }

        monitoring_data["alerts"] = [
            {"type": "queue_stuck", "message": "队列长时间未更新", "queue_name": "test_queue"},
            {"type": "resource_high", "message": "CPU使用率超过阈值", "resource": "cpu"},
        ]

        monitoring_data["last_update"] = datetime.now().isoformat()


def monitoring_worker():
    """监控工作线程"""
    print("📊 启动监控数据收集线程...")
    while True:
        try:
            collect_monitoring_data()
            time.sleep(30)  # 每30秒更新一次
        except Exception as e:
            print(f"❌ 监控数据收集出错: {e}")
            time.sleep(60)


# Flask路由
@app.route("/")
def index():
    """主仪表板页面"""
    if not FLASK_AVAILABLE:
        return "Flask未安装，请运行: pip install flask", 500

    return render_template(
        "dashboard.html",
        queues=monitoring_data["queues"],
        system_resources=monitoring_data["system_resources"],
        alerts=monitoring_data["alerts"],
        last_update=monitoring_data["last_update"],
    )


@app.route("/api/status")
def api_status():
    """API端点：获取监控状态"""
    return jsonify(
        {
            "status": "ok",
            "data": {
                "queues": monitoring_data["queues"],
                "system_resources": monitoring_data["system_resources"],
                "alerts": monitoring_data["alerts"],
                "last_update": monitoring_data["last_update"],
                "queues_count": len(monitoring_data["queues"]),
                "alerts_count": len(monitoring_data["alerts"]),
            },
        }
    )


@app.route("/api/history")
def api_history():
    """API端点：获取历史数据"""
    return jsonify({"status": "ok", "data": monitoring_data["history"]})


@app.route("/api/queue/<queue_name>/details")
def api_queue_details(queue_name):
    """API端点：获取队列详情"""
    for queue in monitoring_data["queues"]:
        if queue["name"] == queue_name:
            return jsonify({"status": "ok", "data": queue})

    return jsonify({"status": "error", "message": f"队列 '{queue_name}' 未找到"}), 404


@app.route("/api/alert/summary")
def api_alert_summary():
    """API端点：获取告警摘要"""
    alert_summary = {}
    for alert in monitoring_data["alerts"]:
        alert_type = alert.get("type", "unknown")
        alert_summary[alert_type] = alert_summary.get(alert_type, 0) + 1

    return jsonify(
        {
            "status": "ok",
            "data": {
                "total_alerts": len(monitoring_data["alerts"]),
                "alert_summary": alert_summary,
                "alerts": monitoring_data["alerts"][:20],  # 返回前20个告警
            },
        }
    )


# 创建HTML模板
def create_html_template():
    """创建HTML模板文件"""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)

    # 创建dashboard.html
    dashboard_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Athena队列监控仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #2c3e50;
            font-size: 2.2rem;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .header h1 .icon {
            font-size: 2.5rem;
        }

        .last-update {
            color: #7f8c8d;
            font-size: 0.9rem;
        }

        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
            margin-left: 15px;
        }

        .status-running {
            background: #d4edda;
            color: #155724;
        }

        .status-paused {
            background: #fff3cd;
            color: #856404;
        }

        .status-error {
            background: #f8d7da;
            color: #721c24;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 25px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f1f1f1;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card h2 .count {
            background: #3498db;
            color: white;
            padding: 3px 12px;
            border-radius: 15px;
            font-size: 0.9rem;
        }

        .queue-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
        }

        .queue-item.running {
            border-left-color: #28a745;
        }

        .queue-item.paused {
            border-left-color: #ffc107;
        }

        .queue-item.error {
            border-left-color: #dc3545;
        }

        .queue-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .queue-name {
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1rem;
        }

        .queue-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 10px;
        }

        .stat-item {
            text-align: center;
            padding: 8px;
            background: white;
            border-radius: 8px;
        }

        .stat-value {
            font-size: 1.2rem;
            font-weight: bold;
            color: #2c3e50;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #7f8c8d;
        }

        .alert-item {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
        }

        .alert-item.error {
            background: #f8d7da;
            border-left-color: #dc3545;
        }

        .alert-time {
            font-size: 0.8rem;
            color: #7f8c8d;
            margin-top: 5px;
        }

        .resource-meter {
            margin-bottom: 20px;
        }

        .meter-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }

        .meter-bar {
            height: 20px;
            background: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
        }

        .meter-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
        }

        .meter-cpu {
            background: linear-gradient(90deg, #3498db, #2980b9);
        }

        .meter-memory {
            background: linear-gradient(90deg, #2ecc71, #27ae60);
        }

        .meter-disk {
            background: linear-gradient(90deg, #9b59b6, #8e44ad);
        }

        .chart-container {
            height: 200px;
            margin-top: 20px;
        }

        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s ease;
        }

        .refresh-btn:hover {
            transform: scale(1.05);
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
            opacity: 0.8;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .header {
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>
                    <span class="icon">📊</span>
                    Athena队列监控仪表板
                </h1>
                <div class="last-update">
                    最后更新: <span id="lastUpdateTime">正在加载...</span>
                </div>
            </div>
            <button class="refresh-btn" onclick="refreshData()">
                <span>🔄</span> 刷新数据
            </button>
        </div>

        <div class="dashboard-grid">
            <!-- 系统资源卡片 -->
            <div class="card">
                <h2>系统资源 <span class="count" id="resourceCount">--</span></h2>
                <div class="resource-meter">
                    <div class="meter-label">
                        <span>CPU使用率</span>
                        <span id="cpuPercent">--%</span>
                    </div>
                    <div class="meter-bar">
                        <div class="meter-fill meter-cpu" id="cpuMeter" style="width: 0%"></div>
                    </div>
                </div>

                <div class="resource-meter">
                    <div class="meter-label">
                        <span>内存使用率</span>
                        <span id="memoryPercent">--%</span>
                    </div>
                    <div class="meter-bar">
                        <div class="meter-fill meter-memory" id="memoryMeter" style="width: 0%"></div>
                    </div>
                </div>

                <div class="resource-meter">
                    <div class="meter-label">
                        <span>磁盘使用率</span>
                        <span id="diskPercent">--%</span>
                    </div>
                    <div class="meter-bar">
                        <div class="meter-fill meter-disk" id="diskMeter" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- 队列状态卡片 -->
            <div class="card">
                <h2>队列状态 <span class="count" id="queueCount">0</span></h2>
                <div id="queuesList">
                    <!-- 队列项将通过JavaScript动态添加 -->
                    <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                        正在加载队列数据...
                    </div>
                </div>
            </div>

            <!-- 告警卡片 -->
            <div class="card">
                <h2>实时告警 <span class="count" id="alertCount">0</span></h2>
                <div id="alertsList">
                    <!-- 告警项将通过JavaScript动态添加 -->
                    <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                        正在加载告警数据...
                    </div>
                </div>
            </div>
        </div>

        <!-- 历史数据图表卡片 -->
        <div class="card">
            <h2>历史趋势</h2>
            <div class="chart-container">
                <canvas id="historyChart"></canvas>
            </div>
        </div>

        <div class="footer">
            Athena队列监控系统 | 实时更新间隔: 30秒 | 监控版本: 1.0.0
        </div>
    </div>

    <script>
        let historyChart = null;

        // 格式化时间
        function formatTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN');
        }

        // 格式化相对时间
        function formatRelativeTime(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);

            if (diffMins < 1) return '刚刚';
            if (diffMins < 60) return `${diffMins}分钟前`;

            const diffHours = Math.floor(diffMins / 60);
            if (diffHours < 24) return `${diffHours}小时前`;

            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays}天前`;
        }

        // 获取队列状态CSS类
        function getQueueStatusClass(status) {
            switch(status) {
                case 'running': return 'running';
                case 'paused':
                case 'manual_hold': return 'paused';
                case 'failed':
                case 'error': return 'error';
                default: return '';
            }
        }

        // 获取队列状态显示文本
        function getQueueStatusText(status) {
            const statusMap = {
                'running': '运行中',
                'paused': '已暂停',
                'manual_hold': '手动暂停',
                'failed': '失败',
                'error': '错误',
                'empty': '空队列',
                'unknown': '未知'
            };
            return statusMap[status] || status;
        }

        // 渲染队列列表
        function renderQueues(queues) {
            const container = document.getElementById('queuesList');
            const countElement = document.getElementById('queueCount');

            countElement.textContent = queues.length;

            if (queues.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #7f8c8d;">没有队列数据</div>';
                return;
            }

            let html = '';
            queues.forEach(queue => {
                const statusClass = getQueueStatusClass(queue.status);
                const statusText = getQueueStatusText(queue.status);
                const lastUpdated = formatRelativeTime(queue.last_updated);

                html += `
                <div class="queue-item ${statusClass}">
                    <div class="queue-header">
                        <div class="queue-name">${queue.name}</div>
                        <div class="status-badge status-${statusClass}">${statusText}</div>
                    </div>
                    <div style="color: #7f8c8d; font-size: 0.9rem;">
                        最后更新: ${lastUpdated}
                        ${queue.age_minutes ? `(${queue.age_minutes.toFixed(1)}分钟前)` : ''}
                    </div>
                    <div class="queue-stats">
                        <div class="stat-item">
                            <div class="stat-value">${queue.tasks.pending}</div>
                            <div class="stat-label">待处理</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${queue.tasks.running}</div>
                            <div class="stat-label">执行中</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${queue.tasks.completed}</div>
                            <div class="stat-label">已完成</div>
                        </div>
                    </div>
                </div>
                `;
            });

            container.innerHTML = html;
        }

        // 渲染告警列表
        function renderAlerts(alerts) {
            const container = document.getElementById('alertsList');
            const countElement = document.getElementById('alertCount');

            countElement.textContent = alerts.length;

            if (alerts.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #7f8c8d;">没有告警</div>';
                return;
            }

            let html = '';
            alerts.slice(0, 10).forEach(alert => { // 显示前10个告警
                const isError = alert.type.includes('error') || alert.type.includes('stuck') || alert.type.includes('failed');
                const alertClass = isError ? 'error' : '';
                const alertTime = alert.timestamp ? formatRelativeTime(alert.timestamp) : '刚刚';

                html += `
                <div class="alert-item ${alertClass}">
                    <strong>${alert.type.toUpperCase()}</strong>
                    <div>${alert.message}</div>
                    <div class="alert-time">${alertTime}</div>
                </div>
                `;
            });

            if (alerts.length > 10) {
                html += `<div style="text-align: center; padding: 10px; color: #7f8c8d;">
                    还有 ${alerts.length - 10} 个告警未显示
                </div>`;
            }

            container.innerHTML = html;
        }

        // 更新系统资源显示
        function updateSystemResources(resources) {
            // CPU
            const cpuPercent = resources.cpu_percent || 0;
            document.getElementById('cpuPercent').textContent = `${cpuPercent.toFixed(1)}%`;
            document.getElementById('cpuMeter').style.width = `${cpuPercent}%`;

            // 内存
            const memoryPercent = resources.memory_percent || 0;
            document.getElementById('memoryPercent').textContent = `${memoryPercent.toFixed(1)}%`;
            document.getElementById('memoryMeter').style.width = `${memoryPercent}%`;

            // 磁盘
            const diskPercent = resources.disk_usage || 0;
            document.getElementById('diskPercent').textContent = `${diskPercent.toFixed(1)}%`;
            document.getElementById('diskMeter').style.width = `${diskPercent}%`;

            // 资源计数
            let resourceCount = 0;
            if (cpuPercent > 80) resourceCount++;
            if (memoryPercent > 80) resourceCount++;
            if (diskPercent > 80) resourceCount++;

            document.getElementById('resourceCount').textContent = resourceCount > 0 ? resourceCount : '正常';
        }

        // 更新历史图表
        function updateHistoryChart(historyData) {
            const ctx = document.getElementById('historyChart').getContext('2d');

            if (historyChart) {
                historyChart.destroy();
            }

            // 准备数据
            const labels = historyData.map(h => new Date(h.timestamp).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'}));
            const cpuData = historyData.map(h => h.cpu_usage);
            const memoryData = historyData.map(h => h.memory_usage);
            const alertsData = historyData.map(h => h.alerts_count);

            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'CPU使用率 (%)',
                            data: cpuData,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: '内存使用率 (%)',
                            data: memoryData,
                            borderColor: '#2ecc71',
                            backgroundColor: 'rgba(46, 204, 113, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: '告警数量',
                            data: alertsData,
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: '百分比/数量'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '时间'
                            }
                        }
                    }
                }
            });
        }

        // 加载监控数据
        async function loadMonitoringData() {
            try {
                const response = await axios.get('/api/status');
                const data = response.data.data;

                // 更新最后更新时间
                document.getElementById('lastUpdateTime').textContent = formatTime(data.last_update);

                // 更新队列数据
                renderQueues(data.queues);

                // 更新系统资源
                updateSystemResources(data.system_resources);

                // 更新告警数据
                renderAlerts(data.alerts);

                // 加载历史数据用于图表
                const historyResponse = await axios.get('/api/history');
                if (historyResponse.data.data.length > 0) {
                    updateHistoryChart(historyResponse.data.data);
                }

                console.log('监控数据更新成功');
            } catch (error) {
                console.error('加载监控数据失败:', error);
                document.getElementById('lastUpdateTime').textContent = '更新失败';
            }
        }

        // 刷新数据
        function refreshData() {
            const btn = document.querySelector('.refresh-btn');
            btn.innerHTML = '<span>⏳</span> 更新中...';
            btn.disabled = true;

            loadMonitoringData().finally(() => {
                setTimeout(() => {
                    btn.innerHTML = '<span>🔄</span> 刷新数据';
                    btn.disabled = false;
                }, 1000);
            });
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            // 首次加载数据
            loadMonitoringData();

            // 每30秒自动刷新
            setInterval(loadMonitoringData, 30000);

            // 添加键盘快捷键
            document.addEventListener('keydown', function(e) {
                if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    refreshData();
                }
            });
        });
    </script>
</body>
</html>
"""

    (templates_dir / "dashboard.html").write_text(dashboard_html, encoding="utf-8")
    print(f"✅ 创建HTML模板: {templates_dir / 'dashboard.html'}")

    # 创建静态目录和简单CSS
    css_content = """/* 额外CSS样式 */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
}

.queue-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 10px;
}

.stat-item {
    text-align: center;
    padding: 8px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.stat-value {
    font-size: 1.2rem;
    font-weight: bold;
    color: #2c3e50;
}

.stat-label {
    font-size: 0.8rem;
    color: #7f8c8d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
"""

    (static_dir / "style.css").write_text(css_content, encoding="utf-8")

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Athena队列监控Web仪表板")
    print("=" * 60)

    # 检查Flask
    if not FLASK_AVAILABLE:
        print("⚠️  Flask未安装，创建HTML模板文件")
        create_html_template()
        print("💡 请运行: pip install flask 然后重新启动仪表板")
        print("📁 已创建HTML模板在 templates/dashboard.html")
        return

    # 创建模板
    create_html_template()

    # 尝试加载队列监控器
    monitor_loaded = load_queue_monitor()
    if not monitor_loaded:
        print("⚠️  使用模拟数据模式")

    # 启动监控数据收集线程
    monitor_thread = threading.Thread(target=monitoring_worker, daemon=True)
    monitor_thread.start()

    print("✅ 监控数据收集线程已启动")
    print("🌐 Web仪表板将在 http://localhost:5002 启动")
    print("📊 监控数据每30秒自动更新")
    print("💡 按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 启动Flask应用
    try:
        app.run(host="0.0.0.0", port=5002, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 仪表板服务器已停止")


if __name__ == "__main__":
    main()
