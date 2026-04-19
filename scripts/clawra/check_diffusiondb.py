#!/usr/bin/env python3
"""检查poloclub/diffusiondb仓库结构"""

import json

import requests


def main():
    url = "https://api.github.com/repos/poloclub/diffusiondb/contents"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            contents = response.json()
            print("poloclub/diffusiondb 根目录内容:")
            for item in contents:
                print(f"  {item['type']:10} {item['name']:30} {item.get('size', '')}")

                # 如果是目录，显示子目录
                if item["type"] == "dir" and item["name"] in ["data", "metadata", "prompts"]:
                    sub_url = f"{url}/{item['name']}"
                    sub_response = requests.get(sub_url, headers=headers, timeout=15)
                    if sub_response.status_code == 200:
                        sub_contents = sub_response.json()
                        print(f"    {item['name']}目录内容:")
                        for sub_item in sub_contents[:10]:  # 只显示前10个
                            print(f"      {sub_item['type']:10} {sub_item['name']:30}")
                        if len(sub_contents) > 10:
                            print(f"      ... 还有 {len(sub_contents)-10} 个文件")
        else:
            print(f"错误: {response.status_code}")
            print(response.text[:200])
    except Exception as e:
        print(f"异常: {e}")


if __name__ == "__main__":
    main()
