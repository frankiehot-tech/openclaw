#!/usr/bin/env python3
"""
DashScope 适配器 v3：修复流式 SSE 格式和动态模型切换。
将 Claude Code 的请求转换为百炼 OpenAI 兼容格式，支持真实流式响应。
"""

import datetime
import json
import logging
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import requests

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
).rstrip("/")
DEFAULT_MODEL = os.getenv("DASHSCOPE_DEFAULT_MODEL", "qwen-max")
LOCAL_HOST = os.getenv("DASHSCOPE_ADAPTER_HOST", "127.0.0.1")
LOCAL_PORT = int(os.getenv("DASHSCOPE_ADAPTER_PORT", "8080"))
REQUEST_TIMEOUT = int(os.getenv("DASHSCOPE_TIMEOUT", "180"))

logging.basicConfig(
    level=getattr(logging, os.getenv("DASHSCOPE_ADAPTER_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SENSITIVE_HEADERS = {"authorization", "x-api-key", "api-key", "proxy-authorization"}


def mask_secret(value):
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def extract_text_content(content):
    """提取纯文本内容。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            text = extract_text_content(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text", ""))
        if "text" in content:
            return str(content.get("text", ""))
        if "content" in content:
            return extract_text_content(content.get("content"))
        return json.dumps(content, ensure_ascii=False)
    return str(content)


class DashScopeAdapter(BaseHTTPRequestHandler):
    """HTTP 请求处理器，完成 Claude Code <-> DashScope 数据格式转换。"""

    def write_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_error_json(self, status_code, message, error_type="api_error"):
        self.write_json(
            status_code,
            {
                "type": "error",
                "error": {
                    "type": error_type,
                    "message": message,
                },
            },
        )

    def log_headers(self):
        logger.debug("头部:")
        for key, value in self.headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                value = mask_secret(value)
            logger.debug("  %s: %s", key, value)

    def resolve_api_key(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        x_api_key = self.headers.get("x-api-key") or self.headers.get("api-key")
        if x_api_key:
            return x_api_key.strip()
        return DASHSCOPE_API_KEY

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/v1", "/v1/"}:
            host = self.headers.get("Host", f"{LOCAL_HOST}:{LOCAL_PORT}")
            response = {
                "object": "api_root",
                "version": "v1",
                "models": f"http://{host}/v1/models",
                "messages": f"http://{host}/v1/messages",
            }
            self.write_json(200, response)
            return

        if path in {"/health", "/v1/health"}:
            response = {
                "status": "healthy",
                "version": "3.0",
                "default_model": DEFAULT_MODEL,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            self.write_json(200, response)
            return

        if path in {"/v1/models", "/v1/models/"}:
            models = [
                "qwen-max", "qwen-plus", "qwen-turbo", "qwen-coder-plus",
                "qwen-long", "qwen3-235B-A22B", "qwen3.6-plus"
            ]
            response = {
                "models": [
                    {
                        "id": m,
                        "name": m,
                        "created": 1775211947,
                        "object": "model",
                        "permissions": ["read", "write"],
                        "owned_by": "dashscope",
                    }
                    for m in models
                ],
                "object": "list",
            }
            self.write_json(200, response)
            return

        if path.startswith("/v1/models/"):
            model_id = path[len("/v1/models/"):]
            response = {
                "id": model_id,
                "name": model_id,
                "created": 1775211947,
                "object": "model",
                "permissions": ["read", "write"],
                "owned_by": "dashscope",
            }
            self.write_json(200, response)
            return

        self.write_error_json(404, f"Unhandled path: {path}", "not_found_error")

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path in {"/", "/v1", "/v1/", "/health", "/v1/health", "/v1/models"} or path.startswith("/v1/models/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.write_error_json(400, "Invalid JSON", "invalid_request_error")
            return

        model = data.get("model", DEFAULT_MODEL)
        logger.info("POST %s: 收到请求，模型=%s, 流式=%s", self.path, model, data.get("stream", False))

        if path != "/v1/messages":
            self.write_error_json(404, f"Unhandled path: {path}", "not_found_error")
            return

        api_key = self.resolve_api_key()
        if not api_key:
            self.write_error_json(401, "Missing DashScope API key", "authentication_error")
            return

        # 转换为 OpenAI 格式
        openai_data = self.convert_to_openai(data, model)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 流式请求：使用真实流式调用
        if data.get("stream", False):
            self.stream_to_client(openai_data, headers)
            return

        # 非流式请求
        try:
            response = requests.post(
                f"{DASHSCOPE_BASE_URL}/chat/completions",
                headers=headers,
                json=openai_data,
                timeout=(5, REQUEST_TIMEOUT),
            )
        except requests.Timeout:
            self.write_error_json(504, f"DashScope upstream timeout after {REQUEST_TIMEOUT}s", "timeout_error")
            return
        except requests.RequestException as exc:
            self.write_error_json(502, f"DashScope upstream request failed: {exc}", "api_error")
            return

        if response.status_code == 200:
            llm_response = self.convert_nonstream_response(response.json(), model)
            self.write_json(200, llm_response)
            logger.info("POST %s: 成功，状态码=%s", self.path, response.status_code)
            return

        try:
            upstream_payload = response.json()
        except ValueError:
            upstream_payload = {
                "type": "error",
                "error": {
                    "type": "upstream_error",
                    "message": response.text[:1000] or "DashScope upstream error",
                },
            }

        self.write_json(response.status_code, upstream_payload)
        logger.error("POST %s: DashScope错误，状态码=%s", self.path, response.status_code)

    # 支持的百炼模型映射
    SUPPORTED_MODELS = {
        "qwen-max", "qwen-plus", "qwen-turbo", "qwen-coder-plus",
        "qwen-long", "qwen3-235B-A22B", "qwen3.6-plus"
    }

    def resolve_model(self, model):
        """将非百炼模型自动映射到默认模型。"""
        if model in self.SUPPORTED_MODELS:
            return model
        # Claude 系列模型映射
        claude_map = {
            "claude-sonnet-4-20250514": "qwen-max",
            "claude-haiku-4-5-20251001": "qwen-turbo",
            "claude-opus-4-20250514": "qwen-max",
        }
        mapped = claude_map.get(model)
        if mapped:
            logger.info("模型映射: %s -> %s", model, mapped)
            return mapped
        # 未知模型 fallback 到默认模型
        logger.warning("未知模型 %s，使用默认模型 %s", model, DEFAULT_MODEL)
        return DEFAULT_MODEL

    def convert_to_openai(self, data, model):
        """将 Claude Code 请求转换为 OpenAI 格式。"""
        model = self.resolve_model(model)
        messages = data.get("messages", [])
        system_blocks = data.get("system", [])

        openai_messages = []
        system_text = extract_text_content(system_blocks)
        if system_text:
            openai_messages.append({"role": "system", "content": system_text})

        for message in messages:
            role = message.get("role", "user")
            if role not in {"assistant", "user", "system"}:
                role = "user"

            content = message.get("content", "")
            if isinstance(content, list):
                # 处理混合内容
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        tool_content = extract_text_content(block.get("content", ""))
                        text_parts.append(f"[Tool Result] {tool_content}")
                content = "\n".join(text_parts).strip()
            else:
                content = extract_text_content(content)

            if content:
                openai_messages.append({"role": role, "content": content})

        # 不同模型的 max_tokens 限制
        model_limits = {
            "qwen-max": 8192,
            "qwen-plus": 8192,
            "qwen-turbo": 8192,
            "qwen-coder-plus": 8192,
            "qwen-long": 8192,
            "qwen3-235B-A22B": 32768,
            "qwen3.6-plus": 32768,
        }
        max_limit = model_limits.get(model, 8192)
        max_tokens = min(data.get("max_tokens", 4096), max_limit)
        
        return {
            "model": model,  # 使用请求中的模型名
            "messages": openai_messages,
            "temperature": data.get("temperature", 0.7),
            "max_tokens": max_tokens,
            "stream": data.get("stream", False),
        }

    def convert_nonstream_response(self, openai_response, model):
        """转换非流式响应为 Claude Code 格式。"""
        choices = openai_response.get("choices", [])
        if not choices:
            return {
                "type": "error",
                "error": {
                    "type": "upstream_error",
                    "message": "No response from model",
                },
            }

        choice = choices[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")

        content_text = extract_text_content(message.get("content", ""))
        content_blocks = []
        if content_text:
            content_blocks = [{"type": "text", "text": content_text}]

        stop_reason_map = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
        }

        return {
            "id": openai_response.get("id", f"msg_{uuid.uuid4().hex[:24]}"),
            "type": "message",
            "role": "assistant",
            "content": content_blocks,
            "model": model,
            "stop_reason": stop_reason_map.get(finish_reason, "end_turn"),
            "usage": {
                "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0),
            },
        }

    def stream_to_client(self, openai_data, headers):
        """使用真实流式调用并将 SSE 事件转发给客户端。"""
        try:
            response = requests.post(
                f"{DASHSCOPE_BASE_URL}/chat/completions",
                headers=headers,
                json=openai_data,
                timeout=(5, REQUEST_TIMEOUT),
                stream=True,
            )
        except requests.Timeout:
            self.write_error_json(504, f"DashScope upstream timeout after {REQUEST_TIMEOUT}s", "timeout_error")
            return
        except requests.RequestException as exc:
            self.write_error_json(502, f"DashScope upstream request failed: {exc}", "api_error")
            return

        # 设置 SSE 响应头
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        model = openai_data.get("model", DEFAULT_MODEL)
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"
        input_tokens = 0
        output_tokens = 0
        accumulated_text = ""

        # 1. message_start
        self._send_sse({
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })

        # 2. 处理流式响应
        content_block_sent = False
        try:
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    line_str = line_str[6:]
                if line_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(line_str)
                except json.JSONDecodeError:
                    continue

                # 提取 token 用量
                usage = chunk.get("usage")
                if usage:
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")

                # 首次响应先发送 content_block_start
                if not content_block_sent:
                    content_block_sent = True
                    self._send_sse({
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {"type": "text", "text": ""},
                    })

                # 提取文本
                text = delta.get("content", "")
                if text:
                    accumulated_text += text
                    self._send_sse({
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": text},
                    })
        except BrokenPipeError:
            logger.warning("客户端断开连接，流式传输中断")
            return

        # 3. content_block_stop
        self._send_sse({
            "type": "content_block_stop",
            "index": 0,
        })

        # 4. message_delta
        stop_reason = "end_turn"
        self._send_sse({
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        })

        # 更新 usage
        self._send_sse({
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason},
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        })

        # 5. message_stop
        self._send_sse({"type": "message_stop"})

    def _send_sse(self, event):
        """发送一个 SSE 事件。"""
        data = json.dumps(event, ensure_ascii=False)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def main():
    print("🚀 DashScope 适配器 v3 启动中...")
    print(f"   本地监听: http://{LOCAL_HOST}:{LOCAL_PORT}")
    print(f"   目标端点: {DASHSCOPE_BASE_URL}")
    print(f"   默认模型: {DEFAULT_MODEL}")
    print(f"   支持模型: qwen-max, qwen-plus, qwen-turbo, qwen-coder-plus, qwen-long")
    if DASHSCOPE_API_KEY:
        print(f"   密钥状态: 已配置 (已脱敏)")
    else:
        print(f"   密钥状态: 未设置 (依赖调用方传入)")
    print()
    print("📋 使用方法:")
    print(f"   1. 设置环境变量: export LLM_BASE_URL=http://{LOCAL_HOST}:{LOCAL_PORT}")
    print("   2. 启动 Claude Code: claude")
    print()

    server = ThreadingHTTPServer((LOCAL_HOST, LOCAL_PORT), DashScopeAdapter)
    print(f"✅ 适配器 v3 已在 http://{LOCAL_HOST}:{LOCAL_PORT} 启动")
    print("   Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 适配器已停止")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()