#!/usr/bin/env python3
"""P0紧急修复：修复Web API认证问题，解决监控脚本401错误"""

import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path("/Volumes/1TB-M2/openclaw").resolve()

# 关键文件路径
QUEUE_MONITOR_SCRIPT = PROJECT_ROOT / "scripts" / "queue_monitor.py"
TOKEN_FILE = PROJECT_ROOT / ".openclaw" / "athena_web_desktop.token"
CONFIG_FILE = PROJECT_ROOT / "scripts" / "queue_monitor_config.yaml"


def read_token():
    """读取认证token"""
    if not TOKEN_FILE.exists():
        print(f"❌ Token文件不存在: {TOKEN_FILE}")
        return None

    token = TOKEN_FILE.read_text().strip()
    print(f"✅ 读取token: {token[:10]}...")
    return token


def fix_queue_monitor_script(token):
    """修复queue_monitor.py脚本，添加认证头"""
    if not QUEUE_MONITOR_SCRIPT.exists():
        print(f"❌ 监控脚本不存在: {QUEUE_MONITOR_SCRIPT}")
        return False

    # 读取脚本内容
    with open(QUEUE_MONITOR_SCRIPT, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找Web API检查部分
    web_api_check = """        # 4. 检查Web API状态（可选）
        try:
            # 尝试连接Athena Web API
            response = requests.get("http://127.0.0.1:8080/api/athena/queues", timeout=5)"""

    # 检查是否已修复（是否包含headers）
    if "X-OpenClaw-Token" in content:
        print("✅ 监控脚本似乎已包含认证头，跳过修复")
        return True

    # 构建带认证头的请求
    fixed_web_api_check = f"""        # 4. 检查Web API状态（可选）
        try:
            # 尝试连接Athena Web API（带认证）
            headers = {{"X-OpenClaw-Token": "{token}"}}
            response = requests.get("http://127.0.0.1:8080/api/athena/queues", headers=headers, timeout=5)"""

    if web_api_check in content:
        # 替换内容
        new_content = content.replace(web_api_check, fixed_web_api_check)

        # 备份原文件
        backup_file = QUEUE_MONITOR_SCRIPT.with_suffix(".py.backup")
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📦 备份原脚本到: {backup_file}")

        # 写入修复后的内容
        with open(QUEUE_MONITOR_SCRIPT, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ 修复监控脚本: {QUEUE_MONITOR_SCRIPT}")
        return True
    else:
        print("❌ 未找到Web API检查代码段，脚本结构可能已变化")
        # 尝试在文件中查找并添加headers参数
        lines = content.split("\n")
        fixed_lines = []
        for i, line in enumerate(lines):
            if 'requests.get("http://127.0.0.1:8080/api/athena/queues"' in line:
                # 修改这一行
                if "headers=" not in line:
                    # 在timeout参数前添加headers参数
                    if "timeout=" in line:
                        line = line.replace(
                            "timeout=", f'headers={{"X-OpenClaw-Token": "{token}"}}, timeout='
                        )
                    else:
                        line = line.replace('")', f'", headers={{"X-OpenClaw-Token": "{token}"}})')
                    print(f"   🔧 修复第{i+1}行: {line[:80]}...")
            fixed_lines.append(line)

        new_content = "\n".join(fixed_lines)

        if new_content != content:
            # 备份并写入
            backup_file = QUEUE_MONITOR_SCRIPT.with_suffix(".py.backup")
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(content)

            with open(QUEUE_MONITOR_SCRIPT, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"✅ 修复监控脚本（动态查找）")
            return True
        else:
            print("❌ 未找到需要修复的API调用")
            return False


def update_config_with_token(token):
    """在配置文件中添加token配置（可选）"""
    if not CONFIG_FILE.exists():
        print(f"⚠️ 配置文件不存在: {CONFIG_FILE}")
        return False

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否已包含web_api配置
    if "web_api:" in content or "auth_token:" in content:
        print("✅ 配置文件似乎已包含Web API配置")
        return True

    # 在文件末尾添加配置
    new_section = f"""
# Web API认证配置（P0修复添加）
web_api:
  base_url: "http://127.0.0.1:8080"
  auth_token: "{token}"
  timeout: 5
"""

    new_content = content.rstrip() + new_section

    # 备份并写入
    backup_file = CONFIG_FILE.with_suffix(".yaml.backup")
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(content)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ 更新配置文件: {CONFIG_FILE}")
    return True


def test_fix():
    """测试修复效果"""
    print("\n🧪 测试修复效果...")

    # 导入修复后的监控脚本进行测试
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

    try:
        import queue_monitor

        print("✅ 监控脚本导入成功")

        # 检查脚本是否包含认证头
        with open(QUEUE_MONITOR_SCRIPT, "r", encoding="utf-8") as f:
            content = f.read()

        if "X-OpenClaw-Token" in content:
            print("✅ 监控脚本包含认证头")
        else:
            print("❌ 监控脚本不包含认证头")

        # 测试Web API调用
        import requests

        token = read_token()
        if token:
            headers = {"X-OpenClaw-Token": token}
            try:
                response = requests.get(
                    "http://127.0.0.1:8080/api/athena/queues", headers=headers, timeout=5
                )
                print(f"✅ Web API测试成功: 状态码 {response.status_code}")
                if response.status_code == 200:
                    print(f"   响应包含 {len(response.json().get('routes', []))} 个队列")
                return True
            except Exception as e:
                print(f"❌ Web API测试失败: {e}")
                return False
        else:
            print("❌ 无法读取token")
            return False
    except ImportError as e:
        print(f"❌ 无法导入监控脚本: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False


def main():
    print("🚀 P0紧急修复：Web API认证问题")
    print("=" * 50)

    # 1. 读取token
    token = read_token()
    if not token:
        return False

    # 2. 修复监控脚本
    print("\n🔧 步骤1: 修复监控脚本...")
    if not fix_queue_monitor_script(token):
        print("❌ 修复监控脚本失败")
        return False

    # 3. 更新配置文件（可选）
    print("\n📝 步骤2: 更新配置文件...")
    update_config_with_token(token)

    # 4. 测试修复
    print("\n🧪 步骤3: 测试修复效果...")
    if test_fix():
        print("\n✅ P0修复完成！监控脚本现在应该能够成功调用Web API")

        # 重启监控守护进程以应用更改
        print("\n🔄 建议重启队列监控守护进程:")
        print("   ./scripts/stop_queue_monitor.sh")
        print("   ./scripts/start_queue_monitor.sh")
        return True
    else:
        print("\n❌ 修复测试失败")
        return False


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
