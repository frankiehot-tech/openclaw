#!/usr/bin/env python3
"""测试原始URL下载"""

import json

import requests


def test_raw_download():
    url = "https://raw.githubusercontent.com/anderlli0053/AppArchive/main/stable-diffusion-prompt-reader_(1).json"
    headers = {"User-Agent": "ClawraPromptCollector/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            print(f"内容长度: {len(content)} 字符")
            print(f"前500字符:")
            print(content[:500])

            # 尝试解析
            try:
                data = json.loads(content)
                print(f"\nJSON解析成功")
                print(f"数据类型: {type(data)}")
                if isinstance(data, dict):
                    print(f"键: {list(data.keys())}")
                    if "prompt" in data:
                        print(f"prompt字段: {data['prompt'][:200]}")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
        else:
            print(f"错误: {response.text[:200]}")
    except Exception as e:
        print(f"异常: {e}")


if __name__ == "__main__":
    test_raw_download()
