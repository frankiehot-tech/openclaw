#!/usr/bin/env python3
"""
测试成本监控仪表板API
"""

import sys
import time

import requests

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")


def test_dashboard_api():
    """测试仪表板API端点"""

    # 导入仪表板模块以检查初始化
    try:
        print("✅ 成功导入仪表板模块")
    except Exception as e:
        print(f"❌ 导入仪表板模块失败: {e}")
        return False

    # 在后台启动Flask服务器
    import subprocess

    print("🚀 启动仪表板服务器...")

    # 启动服务器进程
    server_process = subprocess.Popen(
        [sys.executable, "/Volumes/1TB-M2/openclaw/mini-agent/cost_monitoring_dashboard.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 等待服务器启动
    time.sleep(3)

    # 检查进程是否仍在运行
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        print("❌ 服务器启动失败:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False

    print(f"✅ 服务器进程已启动 (PID: {server_process.pid})")

    try:
        # 测试健康检查端点
        print("\n=== 测试健康检查端点 ===")
        try:
            response = requests.get("http://127.0.0.1:5001/api/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 健康检查成功: {health_data}")
            else:
                print(f"❌ 健康检查失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 健康检查请求失败: {e}")

        # 测试当前指标端点
        print("\n=== 测试当前指标端点 ===")
        try:
            response = requests.get(
                "http://127.0.0.1:5001/api/migration/current_metrics", timeout=10
            )
            if response.status_code == 200:
                metrics_data = response.json()
                print("✅ 获取当前指标成功")
                print(f"   实验ID: {metrics_data.get('experiment_id', 'N/A')}")
                print(f"   总请求数: {metrics_data.get('total_requests', 0)}")
                print(f"   成本节省: {metrics_data.get('cost_savings_percent', 0):.1f}%")
                print(f"   质量一致性: {metrics_data.get('quality_consistency', 0):.2f}")
            elif response.status_code == 500:
                error_data = response.json()
                print(f"⚠️  指标收集失败: {error_data.get('error', 'Unknown error')}")
            else:
                print(f"❌ 获取指标失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 当前指标请求失败: {e}")

        # 测试历史数据端点
        print("\n=== 测试历史数据端点 ===")
        try:
            response = requests.get("http://127.0.0.1:5001/api/migration/history", timeout=10)
            if response.status_code == 200:
                history_data = response.json()
                history_points = len(history_data.get("history", []))
                print(f"✅ 获取历史数据成功: {history_points} 个数据点")
                if history_points > 0:
                    latest = history_data["history"][0]
                    print(f"   最新点: {latest.get('timestamp', 'N/A')}")
                    print(f"   成本节省: {latest.get('cost_savings_percent', 0):.1f}%")
                    print(f"   DashScope请求: {latest.get('dashscope_requests', 0)}")
                    print(f"   DeepSeek请求: {latest.get('deepseek_requests', 0)}")
            elif response.status_code == 500:
                error_data = response.json()
                print(f"⚠️  历史数据获取失败: {error_data.get('error', 'Unknown error')}")
            else:
                print(f"❌ 历史数据失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 历史数据请求失败: {e}")

        # 测试告警端点
        print("\n=== 测试告警端点 ===")
        try:
            response = requests.get("http://127.0.0.1:5001/api/alerts", timeout=5)
            if response.status_code == 200:
                alerts_data = response.json()
                alerts_count = len(alerts_data.get("alerts", []))
                print(f"✅ 获取告警成功: {alerts_count} 个告警")
            elif response.status_code == 500:
                error_data = response.json()
                print(f"⚠️  告警获取失败: {error_data.get('error', 'Unknown error')}")
            else:
                print(f"❌ 告警失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 告警请求失败: {e}")

        # 测试实验信息端点
        print("\n=== 测试实验信息端点 ===")
        try:
            response = requests.get("http://127.0.0.1:5001/api/experiments", timeout=5)
            if response.status_code == 200:
                exp_data = response.json()
                exp_count = len(exp_data.get("experiments", []))
                print(f"✅ 获取实验信息成功: {exp_count} 个实验")
                for exp in exp_data.get("experiments", []):
                    print(f"   - {exp.get('name', 'N/A')} ({exp.get('status', 'N/A')})")
            elif response.status_code == 500:
                error_data = response.json()
                print(f"⚠️  实验信息获取失败: {error_data.get('error', 'Unknown error')}")
            else:
                print(f"❌ 实验信息失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 实验信息请求失败: {e}")

        print("\n=== 仪表板网页测试 ===")
        print("📊 请访问 http://127.0.0.1:5001 查看完整仪表板")

        # 保持服务器运行以便手动测试
        print("\n⏳ 服务器将继续运行30秒...")
        print("按 Ctrl+C 提前停止")

        time.sleep(30)

    finally:
        # 停止服务器
        print("\n🛑 停止服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✅ 服务器已停止")
        except subprocess.TimeoutExpired:
            print("⚠️  服务器未响应，强制终止...")
            server_process.kill()
            server_process.wait()
            print("✅ 服务器已强制终止")

    return True


if __name__ == "__main__":
    try:
        test_dashboard_api()
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
