#!/usr/bin/env python3
"""
Qwen模型命令行工具
通过DashScope OpenAI兼容API调用Qwen模型
"""

import os
import sys
import json
import argparse
import requests
from typing import List, Dict, Optional

# 默认配置
DEFAULT_API_KEY = ""
DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.6-plus"

class QwenCLI:
    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIYUN_API_KEY") or DEFAULT_API_KEY
        self.api_base = api_base or DEFAULT_API_BASE
        self.model = model or DEFAULT_MODEL
        self.api_url = f"{self.api_base}/chat/completions"

        if not self.api_key:
            raise ValueError("缺少 DASHSCOPE_API_KEY 或 ALIYUN_API_KEY")

    def chat(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """发送聊天请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return f"错误: 响应格式异常\n{json.dumps(result, indent=2, ensure_ascii=False)}"

        except requests.exceptions.RequestException as e:
            return f"请求错误: {e}"
        except json.JSONDecodeError as e:
            return f"JSON解析错误: {e}"

    def single_query(self, query: str) -> str:
        """单次查询"""
        messages = [{"role": "user", "content": query}]
        return self.chat(messages)

    def interactive(self):
        """交互式聊天"""
        print(f"🤖 Qwen模型交互式聊天 (模型: {self.model})")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'model <模型名称>' 切换模型")
        print("=" * 50)

        messages = []

        while True:
            try:
                user_input = input("\n👤 你: ").strip()

                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("再见！")
                    break

                elif user_input.lower().startswith('model '):
                    new_model = user_input[6:].strip()
                    self.model = new_model
                    print(f"✅ 已切换到模型: {new_model}")
                    continue

                # 添加用户消息
                messages.append({"role": "user", "content": user_input})

                # 获取回复
                print("🤖 Qwen: ", end="", flush=True)
                response = self.chat(messages)
                print(response)

                # 添加助手回复到消息历史
                messages.append({"role": "assistant", "content": response})

                # 保持消息历史不超过10条（可选）
                if len(messages) > 10:
                    messages = messages[-10:]

            except KeyboardInterrupt:
                print("\n\n会话结束")
                break
            except Exception as e:
                print(f"错误: {e}")

def main():
    parser = argparse.ArgumentParser(description="Qwen模型命令行工具")
    parser.add_argument("query", nargs="?", help="直接查询的问题（如不提供则进入交互模式）")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"模型名称（默认: {DEFAULT_MODEL}）")
    parser.add_argument("--api-key", "-k", help="API密钥（默认使用 DASHSCOPE_API_KEY / ALIYUN_API_KEY 环境变量）")
    parser.add_argument("--temperature", "-t", type=float, default=0.7, help="温度参数（默认: 0.7）")
    parser.add_argument("--max-tokens", "-n", type=int, default=2000, help="最大token数（默认: 2000）")
    parser.add_argument("--list-models", "-l", action="store_true", help="列出可用模型")

    args = parser.parse_args()

    cli = QwenCLI(api_key=args.api_key, model=args.model)

    if args.list_models:
        print("获取模型列表...")
        # 这里可以添加获取模型列表的功能
        print("注：使用 curl 获取完整模型列表：")
        print(f'curl -X GET "https://dashscope.aliyuncs.com/api/v1/models" \\')
        print(f'  -H "Authorization: Bearer {cli.api_key[:10]}..." \\')
        print('  -H "Content-Type: application/json"')
        return

    if args.query:
        # 单次查询模式
        response = cli.single_query(args.query)
        print(response)
    else:
        # 交互模式
        cli.interactive()

if __name__ == "__main__":
    main()
