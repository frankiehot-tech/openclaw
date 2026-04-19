#!/usr/bin/env python3
"""下载portrait.md文件查看内容"""

import requests

url = "https://raw.githubusercontent.com/mehakjain07/stable-diffusion-prompts-collection/main/prompts/portrait.md"

try:
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        content = response.text
        print("portrait.md 内容预览:")
        print("=" * 80)
        print(content[:2000])  # 显示前2000字符
        print("\n" + "=" * 80)

        # 统计行数
        lines = content.split("\n")
        print(f"文件总行数: {len(lines)}")

        # 显示非空行
        non_empty = [line for line in lines if line.strip()]
        print(f"非空行数: {len(non_empty)}")

        print("\n前20个非空行:")
        for i, line in enumerate(non_empty[:20]):
            print(f"{i+1}: {line}")
    else:
        print(f"错误: {response.status_code}")
except Exception as e:
    print(f"异常: {e}")
