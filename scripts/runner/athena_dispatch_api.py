#!/usr/bin/env python3
"""
Athena Dispatch API - 最小远程派发 MVP

提供 HTTP API 用于远程创建任务、查询状态、审批、中断。
P0 仅要求最小闭环，不要求完整认证、负载均衡等。

启动方式：
  python scripts/athena_dispatch_api.py [--port 8080] [--host 127.0.0.1]
"""

import argparse
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入 Athena 组件
IMPORT_SUCCESS = False
try:
    # 添加 mini-agent 目录到路径
    mini_agent_path = os.path.join(project_root, "mini-agent")
    if mini_agent_path not in sys.path:
        sys.path.insert(0, mini_agent_path)

    from agent.core.athena_bridge import get_bridge
    from agent.core.athena_orchestrator import get_orchestrator

    IMPORT_SUCCESS = True
    print("✅ Athena 组件导入成功")
except ImportError as e:
    print(f"导入 Athena 组件失败: {e}")
    print("请确保在项目根目录运行")
    IMPORT_SUCCESS = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DispatchAPIHandler(BaseHTTPRequestHandler):
    """Dispatch API 请求处理器"""

    def _send_response(self, status_code: int, data: dict[str, Any]):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        response_json = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode("utf-8"))

    def do_OPTIONS(self):
        """处理 OPTIONS 请求（CORS）"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_response(200, {"status": "ok", "service": "athena_dispatch_api"})
        elif path == "/status":
            # 查询任务状态
            query = parse_qs(parsed.query)
            task_id = query.get("task_id", [None])[0]
            if not task_id:
                self._send_response(400, {"error": "缺少 task_id 参数"})
                return

            orchestrator = get_orchestrator()
            task = orchestrator.get_task(task_id)
            if not task:
                self._send_response(404, {"error": f"任务不存在: {task_id}"})
                return

            self._send_response(
                200,
                {
                    "task_id": task_id,
                    "status": task.get("status"),
                    "approval_state": task.get("approval_state"),
                    "selected_provider": task.get("selected_provider"),
                    "selected_model": task.get("selected_model"),
                    "estimated_cost": task.get("estimated_cost"),
                    "actual_cost": task.get("actual_cost"),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                },
            )
        else:
            self._send_response(404, {"error": f"端点不存在: {path}"})

    def do_POST(self):
        """处理 POST 请求"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_response(400, {"error": "无效的 JSON 数据"})
                return
        else:
            data = {}

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/create":
            self._handle_create(data)
        elif path == "/approve":
            self._handle_approve(data)
        elif path == "/reject":
            self._handle_reject(data)
        elif path == "/interrupt":
            self._handle_interrupt(data)
        else:
            self._send_response(404, {"error": f"端点不存在: {path}"})

    def _handle_create(self, data: dict[str, Any]):
        """处理任务创建"""
        message = data.get("message", "")
        context = data.get("context", {})

        if not message:
            self._send_response(400, {"error": "缺少 message 字段"})
            return

        # 标记为 API 派发
        context["dispatch_source"] = "api"
        context["dispatch_thread_id"] = data.get("thread_id")

        try:
            bridge = get_bridge()
            result = bridge.chat(message, context)

            if result.get("success"):
                task_id = result.get("task_id")
                self._send_response(
                    201,
                    {
                        "success": True,
                        "task_id": task_id,
                        "approval_state": result.get("task_metadata", {}).get("approval_state"),
                        "provider": result.get("task_metadata", {}).get("selected_provider"),
                        "model": result.get("task_metadata", {}).get("selected_model"),
                        "estimated_cost": result.get("task_metadata", {}).get("estimated_cost"),
                        "message": "任务创建成功",
                        "result": result,
                    },
                )
            else:
                self._send_response(
                    400,
                    {
                        "success": False,
                        "error": result.get("error", "未知错误"),
                    },
                )
        except Exception as e:
            logger.error(f"创建任务失败: {e}", exc_info=True)
            self._send_response(500, {"error": f"服务器内部错误: {str(e)}"})

    def _handle_approve(self, data: dict[str, Any]):
        """处理任务批准"""
        task_id = data.get("task_id")
        approved_by = data.get("approved_by", "api")

        if not task_id:
            self._send_response(400, {"error": "缺少 task_id 字段"})
            return

        try:
            orchestrator = get_orchestrator()
            success, message = orchestrator.approve_task(task_id, approved_by)

            if success:
                self._send_response(200, {"success": True, "message": message})
            else:
                self._send_response(400, {"success": False, "error": message})
        except Exception as e:
            logger.error(f"批准任务失败: {e}", exc_info=True)
            self._send_response(500, {"error": f"服务器内部错误: {str(e)}"})

    def _handle_reject(self, data: dict[str, Any]):
        """处理任务拒绝"""
        task_id = data.get("task_id")
        reason = data.get("reason", "")
        rejected_by = data.get("rejected_by", "api")

        if not task_id:
            self._send_response(400, {"error": "缺少 task_id 字段"})
            return

        try:
            orchestrator = get_orchestrator()
            success, message = orchestrator.reject_task(task_id, reason, rejected_by)

            if success:
                self._send_response(200, {"success": True, "message": message})
            else:
                self._send_response(400, {"success": False, "error": message})
        except Exception as e:
            logger.error(f"拒绝任务失败: {e}", exc_info=True)
            self._send_response(500, {"error": f"服务器内部错误: {str(e)}"})

    def _handle_interrupt(self, data: dict[str, Any]):
        """处理任务中断"""
        task_id = data.get("task_id")
        reason = data.get("reason", "")
        interrupted_by = data.get("interrupted_by", "api")

        if not task_id:
            self._send_response(400, {"error": "缺少 task_id 字段"})
            return

        try:
            orchestrator = get_orchestrator()
            success, message = orchestrator.interrupt_task(task_id, reason, interrupted_by)

            if success:
                self._send_response(200, {"success": True, "message": message})
            else:
                self._send_response(400, {"success": False, "error": message})
        except Exception as e:
            logger.error(f"中断任务失败: {e}", exc_info=True)
            self._send_response(500, {"error": f"服务器内部错误: {str(e)}"})

    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(host: str = "127.0.0.1", port: int = 8080):
    """运行 HTTP 服务器"""
    if not IMPORT_SUCCESS:
        print("❌ 导入 Athena 组件失败，无法启动服务器")
        sys.exit(1)

    server = HTTPServer((host, port), DispatchAPIHandler)
    logger.info(f"Athena Dispatch API 启动于 http://{host}:{port}")
    logger.info("可用端点:")
    logger.info("  POST /create - 创建任务")
    logger.info("  GET  /status?task_id=<id> - 查询任务状态")
    logger.info("  POST /approve - 批准任务")
    logger.info("  POST /reject - 拒绝任务")
    logger.info("  POST /interrupt - 中断任务")
    logger.info("  GET  /health - 健康检查")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到关闭信号，停止服务器")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Athena Dispatch API 服务器")
    parser.add_argument("--host", default="127.0.0.1", help="绑定主机 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="绑定端口 (默认: 8080)")
    parser.add_argument("--daemon", action="store_true", help="以守护进程方式运行")

    args = parser.parse_args()

    if args.daemon:
        # 简单守护进程（仅后台运行，不完善）
        thread = threading.Thread(target=run_server, args=(args.host, args.port))
        thread.daemon = True
        thread.start()
        print(f"Athena Dispatch API 已后台启动于 http://{args.host}:{args.port}")
        print("按 Ctrl+C 停止")
        try:
            while True:
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            print("停止服务器")
    else:
        run_server(args.host, args.port)
