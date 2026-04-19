#!/usr/bin/env python3
"""
调试密码长度问题
"""

import os

# 直接读取.env文件
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
print(f"检查.env文件: {env_file}")

with open(env_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    if "SMTP_PASSWORD" in line:
        print(f"原始行: {repr(line)}")
        if "=" in line:
            key, value = line.split("=", 1)
            print(f"键: {repr(key)}")
            print(f"值: {repr(value)}")
            print(f"值长度: {len(value)}")
            print(f"值字符: {[ord(c) for c in value]}")

# 检查环境变量
print(f"\n环境变量 SMTP_PASSWORD: {repr(os.getenv('SMTP_PASSWORD'))}")
if os.getenv("SMTP_PASSWORD"):
    pwd = os.getenv("SMTP_PASSWORD")
    print(f"长度: {len(pwd)}")
    print(f"字符: {[ord(c) for c in pwd]}")

# 检查其他关键变量
print(f"\n其他关键变量:")
for var in ["WECOM_WEBHOOK_URL", "SMTP_SERVER", "SMTP_USERNAME", "SMTP_PORT"]:
    print(f"{var}: {repr(os.getenv(var))}")
