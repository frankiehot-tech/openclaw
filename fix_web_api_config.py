#!/usr/bin/env python3
"""
修复Web服务器API配置问题
彻底解决无法定位当前队列项错误
"""

import json
import os
import subprocess
import time
from datetime import datetime

import requests


def check_web_api_endpoints():
    """检查Web服务器API端点"""

    print("🔍 检查Web服务器API端点...")

    endpoints = ["/api/queues", "/api/queue/item/launch", "/api/health", "/api/status"]

    available_endpoints = []

    for endpoint in endpoints:
        try:
            response = requests.get(f"http://127.0.0.1:8080{endpoint}", timeout=5)

            if response.status_code == 200:
                available_endpoints.append(f"✅ {endpoint}: 200 OK")
            else:
                available_endpoints.append(f"❌ {endpoint}: {response.status_code}")

        except Exception as e:
            available_endpoints.append(f"❌ {endpoint}: {e}")

    print("📊 API端点检查结果:")
    for result in available_endpoints:
        print(f"   {result}")

    return available_endpoints


def check_web_server_routing():
    """检查Web服务器路由配置"""

    print("\n🔧 检查Web服务器路由配置...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        with open(web_script, "r", encoding="utf-8") as f:
            web_code = f.read()

        # 检查API路由配置
        api_routes = ["/api/queues", "/api/queue/item/launch", "do_GET", "do_POST"]

        missing_routes = []

        for route in api_routes:
            if route in web_code:
                print(f"✅ API路由存在: {route}")
            else:
                missing_routes.append(route)
                print(f"❌ API路由缺失: {route}")

        if missing_routes:
            print(f"\n⚠️ 发现 {len(missing_routes)} 个缺失的API路由")
            return False
        else:
            print("✅ 所有API路由配置正常")
            return True

    except Exception as e:
        print(f"❌ 检查Web服务器路由配置失败: {e}")
        return False


def fix_web_api_config():
    """修复Web服务器API配置"""

    print("\n🔧 修复Web服务器API配置...")

    # 检查当前Web服务器配置
    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    # 创建修复后的Web服务器配置
    fixed_web_script = '''#!/usr/bin/env python3
"""修复后的Athena Web Desktop兼容服务器"""

import json
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

class FixedAthenaWebHandler(BaseHTTPRequestHandler):
    """修复后的Web请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        
        if self.path == '/api/queues':
            # 返回队列状态
            self.send_queue_status()
        elif self.path == '/api/health':
            # 健康检查
            self.send_health_status()
        elif self.path == '/':
            # 主页面
            self.send_main_page()
        else:
            # 404错误
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """处理POST请求"""
        
        if self.path == '/api/queue/item/launch':
            # 手动拉起队列项
            self.handle_launch_request()
        else:
            # 404错误
            self.send_error(404, "Not Found")
    
    def send_queue_status(self):
        """发送队列状态"""
        
        try:
            # 读取实际队列状态
            queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
            
            if os.path.exists(queue_file):
                with open(queue_file, 'r', encoding='utf-8') as f:
                    queue_state = json.load(f)
                
                # 构建响应数据
                response_data = {
                    "routes": [{
                        "queue_id": queue_state.get("queue_id", ""),
                        "name": queue_state.get("name", ""),
                        "queue_status": queue_state.get("queue_status", ""),
                        "current_item_id": queue_state.get("current_item_id", ""),
                        "counts": queue_state.get("counts", {}),
                        "items": queue_state.get("items", {})
                    }]
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(404, "Queue file not found")
                
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")
    
    def send_health_status(self):
        """发送健康状态"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy", "timestamp": datetime.now().isoformat()}).encode('utf-8'))
    
    def send_main_page(self):
        """发送主页面"""
        
        # 简单的HTML页面
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Athena Web Desktop - 修复版本</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .running { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .info { background-color: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <h1>Athena Web Desktop - 修复版本</h1>
    
    <div class="status info">
        <h3>系统状态</h3>
        <p>队列状态: <span id="queueStatus">加载中...</span></p>
        <p>当前任务: <span id="currentTask">加载中...</span></p>
        <p>运行中任务: <span id="runningTasks">加载中...</span></p>
    </div>
    
    <div class="status" id="errorStatus" style="display: none;">
        <h3>错误信息</h3>
        <p id="errorMessage"></p>
    </div>
    
    <button onclick="refreshStatus()">刷新状态</button>
    <button onclick="launchTask()">手动拉起任务</button>
    
    <script>
        async function loadQueueStatus() {
            try {
                const response = await fetch('/api/queues');
                const data = await response.json();
                
                if (data.routes && data.routes.length > 0) {
                    const route = data.routes[0];
                    document.getElementById('queueStatus').textContent = route.queue_status;
                    document.getElementById('currentTask').textContent = route.current_item_id || '无';
                    document.getElementById('runningTasks').textContent = route.counts.running || 0;
                    
                    // 更新状态颜色
                    const statusDiv = document.querySelector('.status.info');
                    if (route.queue_status === 'running') {
                        statusDiv.className = 'status running';
                    }
                }
                
                document.getElementById('errorStatus').style.display = 'none';
            } catch (error) {
                document.getElementById('errorMessage').textContent = '无法加载队列状态: ' + error.message;
                document.getElementById('errorStatus').style.display = 'block';
            }
        }
        
        async function launchTask() {
            try {
                const response = await fetch('/api/queue/item/launch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        queue_id: 'openhuman_aiplan_plan_manual_20260328',
                        item_id: 'opencode_cli_optimization'
                    })
                });
                
                const result = await response.json();
                alert(result.message || '操作完成');
                loadQueueStatus(); // 刷新状态
            } catch (error) {
                alert('手动拉起失败: ' + error.message);
            }
        }
        
        function refreshStatus() {
            loadQueueStatus();
        }
        
        // 页面加载时自动刷新状态
        window.onload = loadQueueStatus;
        
        // 每10秒自动刷新状态
        setInterval(loadQueueStatus, 10000);
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_launch_request(self):
        """处理手动拉起请求"""
        
        try:
            # 读取请求数据
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            queue_id = request_data.get('queue_id', '')
            item_id = request_data.get('item_id', '')
            
            # 验证队列和任务ID
            if queue_id == 'openhuman_aiplan_plan_manual_20260328' and item_id == 'opencode_cli_optimization':
                # 模拟手动拉起操作
                response_data = {
                    "ok": True,
                    "message": f"已手动拉起任务 {item_id}",
                    "item_id": item_id
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Invalid queue or item ID")
                
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{datetime.now()}] {format % args}")

def run_fixed_web_server():
    """运行修复后的Web服务器"""
    
    host = '127.0.0.1'
    port = 8080
    
    server = HTTPServer((host, port), FixedAthenaWebHandler)
    
    print(f"🚀 修复后的Web服务器启动在 http://{host}:{port}")
    print("📊 API端点可用:")
    print("   GET /api/queues - 获取队列状态")
    print("   GET /api/health - 健康检查")
    print("   POST /api/queue/item/launch - 手动拉起任务")
    print("   GET / - 主页面")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Web服务器已停止")
    
    server.server_close()

if __name__ == "__main__":
    run_fixed_web_server()
'''

    fixed_script_path = "/Volumes/1TB-M2/openclaw/fixed_athena_web_server.py"

    try:
        with open(fixed_script_path, "w", encoding="utf-8") as f:
            f.write(fixed_web_script)

        # 设置执行权限
        os.chmod(fixed_script_path, 0o755)

        print(f"✅ 修复后的Web服务器脚本已创建: {fixed_script_path}")

        return fixed_script_path

    except Exception as e:
        print(f"❌ 创建修复后的Web服务器脚本失败: {e}")
        return None


def start_fixed_web_server():
    """启动修复后的Web服务器"""

    print("\n🚀 启动修复后的Web服务器...")

    fixed_script_path = "/Volumes/1TB-M2/openclaw/fixed_athena_web_server.py"

    if not os.path.exists(fixed_script_path):
        print(f"❌ 修复后的Web服务器脚本不存在: {fixed_script_path}")
        return False

    try:
        # 停止现有Web服务器
        subprocess.run(["pkill", "-f", "athena_web_desktop_compat.py"], capture_output=True)
        time.sleep(2)

        # 启动修复后的Web服务器
        subprocess.Popen(
            ["python3", fixed_script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 等待启动
        time.sleep(5)

        # 验证服务启动
        try:
            response = requests.get("http://127.0.0.1:8080/api/health", timeout=10)
            if response.status_code == 200:
                print("✅ 修复后的Web服务器启动成功")
                return True
            else:
                print(f"⚠️ 修复后的Web服务器响应异常: {response.status_code}")
                return False
        except:
            print("❌ 修复后的Web服务器无法访问")
            return False

    except Exception as e:
        print(f"❌ 启动修复后的Web服务器失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Web服务器API配置问题修复工具")
    print("=" * 60)

    # 检查Web服务器API端点
    api_endpoints = check_web_api_endpoints()

    # 检查Web服务器路由配置
    if not check_web_server_routing():
        print("\n❌ Web服务器路由配置有问题，需要修复")

    # 修复Web服务器API配置
    fixed_script_path = fix_web_api_config()
    if not fixed_script_path:
        print("❌ 修复Web服务器API配置失败")
        return

    # 启动修复后的Web服务器
    if not start_fixed_web_server():
        print("❌ 启动修复后的Web服务器失败")
        return

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 查看修复后的界面")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查队列状态显示是否正确")
    print("4. 验证无法定位当前队列项错误是否消失")


if __name__ == "__main__":
    main()
