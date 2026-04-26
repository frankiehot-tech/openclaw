#!/usr/bin/env python3
"""
进程监控仪表板
基于ProcessLifecycleContract的进程监控和管理界面
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from flask import Flask, jsonify, render_template, request

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入Flask
try:
    from flask import Flask, jsonify, render_template, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask未安装，请运行: pip install flask")
    print("💡 将创建命令行监控界面作为替代")

# 尝试导入ProcessLifecycleContract
try:
    from contracts.process_lifecycle import ProcessLifecycleContract

    CONTRACT_AVAILABLE = True
except ImportError as e:
    CONTRACT_AVAILABLE = False
    print(f"⚠️  ProcessLifecycleContract不可用: {e}")
    print("💡 将使用psutil进行基础监控")

app = Flask(__name__)

# 监控数据存储
monitoring_data = {
    "processes": [],
    "system_info": {},
    "contract_status": CONTRACT_AVAILABLE,
    "last_update": None,
    "stats": {
        "total_processes": 0,
        "running": 0,
        "zombie": 0,
        "stale": 0,
        "avg_cpu": 0.0,
        "avg_memory": 0.0,
    },
}

# 更新锁
update_lock = threading.RLock()


def collect_system_info():
    """收集系统信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / 1024 / 1024,
            "memory_total_mb": memory.total / 1024 / 1024,
            "load_1m": load_avg[0],
            "load_5m": load_avg[1],
            "load_15m": load_avg[2],
        }
    except Exception as e:
        return {"timestamp": datetime.now().isoformat(), "error": str(e)}


def collect_processes():
    """收集进程信息"""
    processes = []

    # 检查Athena相关进程
    athena_processes = []

    try:
        # 查找athena_ai_plan_runner.py进程
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "status", "cpu_percent", "memory_percent", "create_time"]
        ):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and len(cmdline) > 1:
                    # 检查是否为Athena相关进程
                    is_athena = any("athena" in str(arg).lower() for arg in cmdline)
                    if is_athena:
                        # 计算进程年龄
                        create_time = proc.info["create_time"]
                        age_seconds = time.time() - create_time
                        age_minutes = age_seconds / 60

                        # 检查心跳状态（如果可能）
                        heartbeat_status = "unknown"
                        heartbeat_age = None

                        # 尝试从队列文件获取心跳信息
                        queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
                        if queue_dir.exists():
                            for queue_file in queue_dir.glob("*.json"):
                                try:
                                    with open(queue_file, "r", encoding="utf-8") as f:
                                        queue_data = json.load(f)

                                    items = queue_data.get("items", {})
                                    for item_id, item in items.items():
                                        runner_pid = item.get("runner_pid")
                                        if runner_pid == proc.info["pid"]:
                                            heartbeat_at = item.get("runner_heartbeat_at")
                                            if heartbeat_at:
                                                try:
                                                    heartbeat_time = datetime.fromisoformat(
                                                        heartbeat_at.replace("Z", "+00:00")
                                                    )
                                                    heartbeat_age = (
                                                        datetime.now() - heartbeat_time
                                                    ).total_seconds()
                                                    if heartbeat_age < 30:  # 30秒内的心跳
                                                        heartbeat_status = "healthy"
                                                    elif heartbeat_age < 60:  # 1分钟内
                                                        heartbeat_status = "warning"
                                                    else:
                                                        heartbeat_status = "stale"
                                                except:
                                                    heartbeat_status = "invalid"
                                except:
                                    pass

                        process_info = {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline_short": " ".join(cmdline[:3])
                            + ("..." if len(cmdline) > 3 else ""),
                            "status": proc.info["status"],
                            "cpu_percent": proc.info["cpu_percent"],
                            "memory_percent": proc.info["memory_percent"],
                            "memory_mb": (
                                proc.memory_info().rss / 1024 / 1024
                                if hasattr(proc, "memory_info")
                                else 0
                            ),
                            "age_minutes": round(age_minutes, 2),
                            "heartbeat_status": heartbeat_status,
                            "heartbeat_age_seconds": heartbeat_age,
                            "is_zombie": proc.info["status"] == psutil.STATUS_ZOMBIE,
                            "create_time": (
                                datetime.fromtimestamp(create_time).isoformat()
                                if create_time
                                else None
                            ),
                        }

                        athena_processes.append(process_info)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except Exception as e:
        print(f"收集进程信息失败: {e}")

    return athena_processes


def update_monitoring_data():
    """更新监控数据"""
    with update_lock:
        try:
            # 收集系统信息
            monitoring_data["system_info"] = collect_system_info()

            # 收集进程信息
            processes = collect_processes()
            monitoring_data["processes"] = processes

            # 计算统计信息
            total = len(processes)
            running = sum(1 for p in processes if p["status"] == "running")
            zombie = sum(1 for p in processes if p["is_zombie"])
            stale = sum(1 for p in processes if p["heartbeat_status"] == "stale")
            avg_cpu = sum(p["cpu_percent"] for p in processes) / total if total > 0 else 0
            avg_memory = sum(p["memory_mb"] for p in processes) / total if total > 0 else 0

            monitoring_data["stats"] = {
                "total_processes": total,
                "running": running,
                "zombie": zombie,
                "stale": stale,
                "avg_cpu": round(avg_cpu, 2),
                "avg_memory": round(avg_memory, 2),
            }

            monitoring_data["last_update"] = datetime.now().isoformat()

            # 检查ProcessLifecycleContract状态
            if CONTRACT_AVAILABLE:
                try:
                    contract = ProcessLifecycleContract()
                    # 测试契约功能
                    monitoring_data["contract_test"] = {
                        "available": True,
                        "heartbeat_interval": 30,
                        "timeout_seconds": 30,
                    }
                except Exception as e:
                    monitoring_data["contract_test"] = {"available": False, "error": str(e)}

            return True

        except Exception as e:
            print(f"更新监控数据失败: {e}")
            return False


# 路由定义
@app.route("/")
def index():
    """主页 - 显示进程监控仪表板"""
    if not FLASK_AVAILABLE:
        return "Flask不可用，请安装flask包: pip install flask", 500

    return render_template("process_monitor.html")


@app.route("/api/status")
def api_status():
    """API端点 - 获取进程状态"""
    update_monitoring_data()
    return jsonify(monitoring_data)


@app.route("/api/processes")
def api_processes():
    """API端点 - 获取进程列表"""
    update_monitoring_data()
    return jsonify(
        {
            "processes": monitoring_data["processes"],
            "stats": monitoring_data["stats"],
            "last_update": monitoring_data["last_update"],
        }
    )


@app.route("/api/system")
def api_system():
    """API端点 - 获取系统信息"""
    update_monitoring_data()
    return jsonify(
        {
            "system_info": monitoring_data["system_info"],
            "last_update": monitoring_data["last_update"],
        }
    )


@app.route("/api/process/<int:pid>/terminate", methods=["POST"])
def api_terminate_process(pid):
    """API端点 - 终止进程"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        time.sleep(0.5)

        if proc.is_running():
            proc.kill()
            return jsonify({"success": True, "message": f"进程 {pid} 已被强制终止", "pid": pid})
        else:
            return jsonify({"success": True, "message": f"进程 {pid} 已终止", "pid": pid})
    except psutil.NoSuchProcess:
        return jsonify({"success": False, "message": f"进程 {pid} 不存在", "pid": pid}), 404
    except psutil.AccessDenied:
        return jsonify({"success": False, "message": f"无权限终止进程 {pid}", "pid": pid}), 403
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"终止进程 {pid} 失败: {str(e)}", "pid": pid}),
            500,
        )


@app.route("/api/contract/test")
def api_contract_test():
    """API端点 - 测试ProcessLifecycleContract"""
    if not CONTRACT_AVAILABLE:
        return jsonify({"available": False, "message": "ProcessLifecycleContract不可用"})

    try:
        contract = ProcessLifecycleContract()

        # 测试基础功能
        test_command = "echo 'ProcessLifecycleContract测试' && sleep 0.5"
        test_result = contract.spawn_with_contract(
            command=test_command, env={"TEST": "true"}, timeout_seconds=5
        )

        return jsonify(
            {
                "available": True,
                "test_result": test_result,
                "heartbeat_interval": 30,
                "timeout_seconds": 30,
                "message": "ProcessLifecycleContract测试成功",
            }
        )
    except Exception as e:
        return jsonify(
            {"available": False, "error": str(e), "message": "ProcessLifecycleContract测试失败"}
        )


# 后台更新线程
def background_updater():
    """后台更新线程"""
    while True:
        try:
            update_monitoring_data()
            time.sleep(10)  # 每10秒更新一次
        except Exception as e:
            print(f"后台更新失败: {e}")
            time.sleep(30)


if __name__ == "__main__":
    # 检查Flask可用性
    if not FLASK_AVAILABLE:
        print("错误: Flask未安装")
        print("请运行: pip install flask")
        sys.exit(1)

    # 检查模板目录
    template_dir = Path("templates")
    if not template_dir.exists():
        template_dir.mkdir(parents=True)

        # 创建基础模板
        template_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>进程监控仪表板 - Athena系统</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-bottom: 5px solid #ff6b6b;
        }
        h1 {
            margin: 0;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .subtitle {
            margin: 10px 0 0;
            opacity: 0.9;
            font-size: 1.2rem;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid #e0e0e0;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.2);
        }
        .card h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-top: 5px;
        }
        .process-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
        }
        .process-item {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            display: grid;
            grid-template-columns: 100px 1fr 100px 100px;
            gap: 10px;
            align-items: center;
        }
        .process-item:last-child {
            border-bottom: none;
        }
        .process-item:hover {
            background: #f8f9fa;
        }
        .pid {
            font-weight: bold;
            color: #3498db;
        }
        .status {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            text-align: center;
            font-weight: bold;
        }
        .status-running { background: #2ecc71; color: white; }
        .status-zombie { background: #e74c3c; color: white; }
        .status-stale { background: #f39c12; color: white; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover {
            background: #c0392b;
            transform: scale(1.05);
        }
        .last-update {
            text-align: center;
            padding: 15px;
            color: #7f8c8d;
            font-style: italic;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
        footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔧 进程监控仪表板</h1>
            <p class="subtitle">基于ProcessLifecycleContract的实时进程监控</p>
        </header>

        <div class="dashboard" id="dashboard">
            <div class="card">
                <h3>📊 系统概览</h3>
                <div class="stats-grid" id="system-stats">
                    <!-- 动态加载 -->
                </div>
                <div id="system-info">
                    <!-- 动态加载 -->
                </div>
            </div>

            <div class="card">
                <h3>🔄 进程统计</h3>
                <div class="stats-grid" id="process-stats">
                    <!-- 动态加载 -->
                </div>
                <div id="contract-info">
                    <!-- 动态加载 -->
                </div>
            </div>

            <div class="card" style="grid-column: span 2;">
                <h3>📋 进程列表 <span id="process-count">(0)</span></h3>
                <div class="process-list" id="process-list">
                    <!-- 动态加载 -->
                </div>
            </div>
        </div>

        <div class="last-update" id="last-update">
            最后更新: <span id="update-time">从未更新</span>
        </div>

        <footer>
            <p>进程监控仪表板 v1.0 | 基于ProcessLifecycleContract | 心跳检测: 30秒</p>
        </footer>
    </div>

    <script>
        let refreshInterval;

        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateSystemStats(data);
                    updateProcessStats(data);
                    updateProcessList(data);
                    updateLastUpdate(data);
                })
                .catch(error => {
                    console.error('更新失败:', error);
                    document.getElementById('last-update').innerHTML =
                        '更新失败: ' + error.message;
                });
        }

        function updateSystemStats(data) {
            const sysInfo = data.system_info;
            if (sysInfo && !sysInfo.error) {
                document.getElementById('system-stats').innerHTML = `
                    <div class="stat">
                        <div class="stat-value">${sysInfo.cpu_percent.toFixed(1)}%</div>
                        <div class="stat-label">CPU使用率</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${sysInfo.memory_percent.toFixed(1)}%</div>
                        <div class="stat-label">内存使用率</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${sysInfo.load_1m.toFixed(2)}</div>
                        <div class="stat-label">1分钟负载</div>
                    </div>
                `;

                document.getElementById('system-info').innerHTML = `
                    <p>内存: ${(sysInfo.memory_used_mb / 1024).toFixed(2)} GB / ${(sysInfo.memory_total_mb / 1024).toFixed(2)} GB</p>
                    <p>负载: ${sysInfo.load_1m.toFixed(2)} (1m) / ${sysInfo.load_5m.toFixed(2)} (5m) / ${sysInfo.load_15m.toFixed(2)} (15m)</p>
                `;
            }
        }

        function updateProcessStats(data) {
            const stats = data.stats;
            document.getElementById('process-stats').innerHTML = `
                <div class="stat">
                    <div class="stat-value">${stats.total_processes}</div>
                    <div class="stat-label">总进程数</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #2ecc71">${stats.running}</div>
                    <div class="stat-label">运行中</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #e74c3c">${stats.zombie}</div>
                    <div class="stat-label">僵尸进程</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #f39c12">${stats.stale}</div>
                    <div class="stat-label">陈旧心跳</div>
                </div>
            `;

            document.getElementById('process-count').textContent = `(${stats.total_processes})`;

            const contractInfo = data.contract_test || {};
            let contractHtml = '<p>ProcessLifecycleContract: ';
            if (contractInfo.available) {
                contractHtml += '<span style="color: #2ecc70">✓ 可用</span>';
                contractHtml += ` | 心跳间隔: ${contractInfo.heartbeat_interval || 30}秒`;
            } else {
                contractHtml += '<span style="color: #e74c3c">✗ 不可用</span>';
                if (contractInfo.error) {
                    contractHtml += `<br>错误: ${contractInfo.error}`;
                }
            }
            contractHtml += '</p>';
            document.getElementById('contract-info').innerHTML = contractHtml;
        }

        function updateProcessList(data) {
            const processes = data.processes || [];
            const processList = document.getElementById('process-list');

            if (processes.length === 0) {
                processList.innerHTML = '<div class="process-item" style="text-align: center; padding: 30px;">未发现Athena相关进程</div>';
                return;
            }

            let html = '';
            processes.forEach(process => {
                let statusClass = 'status-running';
                let statusText = process.status;

                if (process.is_zombie) {
                    statusClass = 'status-zombie';
                    statusText = 'zombie';
                } else if (process.heartbeat_status === 'stale') {
                    statusClass = 'status-stale';
                    statusText = 'stale';
                } else if (process.heartbeat_status === 'warning') {
                    statusClass = 'status-stale';
                    statusText = 'warning';
                }

                html += `
                    <div class="process-item">
                        <div class="pid">PID: ${process.pid}</div>
                        <div title="${process.cmdline_short}">${process.cmdline_short}</div>
                        <div class="status ${statusClass}">${statusText}</div>
                        <div>
                            <button class="btn btn-danger" onclick="terminateProcess(${process.pid})">终止</button>
                        </div>
                    </div>
                `;
            });

            processList.innerHTML = html;
        }

        function updateLastUpdate(data) {
            const timeStr = data.last_update ? new Date(data.last_update).toLocaleTimeString() : '从未更新';
            document.getElementById('update-time').textContent = timeStr;
        }

        function terminateProcess(pid) {
            if (!confirm(`确定要终止进程 ${pid} 吗？`)) {
                return;
            }

            fetch(`/api/process/${pid}/terminate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    setTimeout(updateDashboard, 1000);
                }
            })
            .catch(error => {
                alert('终止进程失败: ' + error.message);
            });
        }

        function startAutoRefresh() {
            updateDashboard();
            refreshInterval = setInterval(updateDashboard, 10000); // 每10秒更新
        }

        function stopAutoRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        }

        // 启动
        document.addEventListener('DOMContentLoaded', startAutoRefresh);

        // 页面可见性变化时控制刷新
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopAutoRefresh();
            } else {
                startAutoRefresh();
            }
        });
    </script>
</body>
</html>
        """
        template_file = template_dir / "process_monitor.html"
        template_file.write_text(template_content, encoding="utf-8")
        print(f"✅ 已创建模板文件: {template_file}")

    # 启动后台更新线程
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()

    print("🚀 启动进程监控仪表板...")
    print("📊 访问地址: http://localhost:5004")
    print("🔧 基于ProcessLifecycleContract的30秒心跳检测")
    print("📈 监控Athena相关进程状态和系统资源")

    # 运行Flask应用
    app.run(host="0.0.0.0", port=5004, debug=False, threaded=True)
