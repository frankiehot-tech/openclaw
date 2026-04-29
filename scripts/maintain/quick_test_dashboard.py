#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
快速测试仪表板API（不使用真实服务器）
"""

import os
import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

# 设置环境变量，防止服务器实际启动
os.environ["FLASK_ENV"] = "testing"

from cost_monitoring_dashboard import app, init_monitors


def test_endpoints():
    """使用Flask测试客户端测试端点"""

    # 初始化监控器
    init_monitors()

    # 创建测试客户端
    with app.test_client() as client:
        print("✅ 创建Flask测试客户端")

        # 测试健康检查
        print("\n1. 测试 /api/health")
        response = client.get("/api/health")
        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✅ 成功: {data}")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")

        # 测试当前指标
        print("\n2. 测试 /api/migration/current_metrics")
        response = client.get("/api/migration/current_metrics")
        if response.status_code == 200:
            data = response.get_json()
            print("   ✅ 成功")
            print(f"     成本节省: {data.get('cost_savings_percent', 0):.1f}%")
            print(f"     总请求数: {data.get('total_requests', 0)}")
            print(f"     DashScope请求: {data.get('dashscope_requests', 0)}")
            print(f"     DeepSeek请求: {data.get('deepseek_requests', 0)}")
        elif response.status_code == 500:
            data = response.get_json()
            print(f"   ❌ 服务器错误: {data.get('error', 'Unknown')}")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")

        # 测试历史数据
        print("\n3. 测试 /api/migration/history")
        response = client.get("/api/migration/history")
        if response.status_code == 200:
            data = response.get_json()
            history_count = len(data.get("history", []))
            print(f"   ✅ 成功: {history_count} 个历史数据点")
            if history_count > 0:
                latest = data["history"][0]
                print(f"     最新点: {latest.get('timestamp', 'N/A')}")
                print(f"     成本节省: {latest.get('cost_savings_percent', 0):.1f}%")
        elif response.status_code == 500:
            data = response.get_json()
            print(f"   ❌ 服务器错误: {data.get('error', 'Unknown')}")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")

        # 测试告警
        print("\n4. 测试 /api/alerts")
        response = client.get("/api/alerts")
        if response.status_code == 200:
            data = response.get_json()
            alerts_count = len(data.get("alerts", []))
            print(f"   ✅ 成功: {alerts_count} 个告警")
        elif response.status_code == 500:
            data = response.get_json()
            print(f"   ❌ 服务器错误: {data.get('error', 'Unknown')}")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")

        # 测试实验信息
        print("\n5. 测试 /api/experiments")
        response = client.get("/api/experiments")
        if response.status_code == 200:
            data = response.get_json()
            exp_count = len(data.get("experiments", []))
            print(f"   ✅ 成功: {exp_count} 个实验")
        elif response.status_code == 500:
            data = response.get_json()
            print(f"   ❌ 服务器错误: {data.get('error', 'Unknown')}")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")

        print("\n✅ 测试完成")


if __name__ == "__main__":
    try:
        test_endpoints()
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
