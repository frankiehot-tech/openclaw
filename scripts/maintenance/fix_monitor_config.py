#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""修复监控配置脚本"""

import os
import re


def fix_monitor_ports():
    """修复监控端口配置"""

    print("🔍 开始修复监控端口配置...")

    # 修复 monitor_web_queue_sync.sh
    sync_script = "/Volumes/1TB-M2/openclaw/monitor_web_queue_sync.sh"
    if os.path.exists(sync_script):
        with open(sync_script) as f:
            content = f.read()

        # 检查当前配置
        if ":3000" in content:
            # 替换端口配置
            content = re.sub(r":3000", ":8080", content)

            with open(sync_script, "w") as f:
                f.write(content)
            print("✅ 修复 monitor_web_queue_sync.sh 端口配置 (3000 → 8080)")
        else:
            print("ℹ️ monitor_web_queue_sync.sh 中未找到3000端口配置")
    else:
        print("⚠️ monitor_web_queue_sync.sh 文件不存在")

    # 修复其他监控脚本
    monitor_files = [
        "/Volumes/1TB-M2/openclaw/monitor_all_queues_protection.sh",
        "/Volumes/1TB-M2/openclaw/monitor_athena_workflow.sh",
        "/Volumes/1TB-M2/openclaw/monitor_config_sync.sh",
        "/Volumes/1TB-M2/openclaw/monitor_queue_protection.sh",
    ]

    for file_path in monitor_files:
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()

            if ":3000" in content:
                content = re.sub(r":3000", ":8080", content)

                with open(file_path, "w") as f:
                    f.write(content)
                print(f"✅ 修复 {os.path.basename(file_path)} 端口配置 (3000 → 8080)")
            else:
                print(f"ℹ️ {os.path.basename(file_path)} 中未找到3000端口配置")
        else:
            print(f"⚠️ {file_path} 文件不存在")


def analyze_api_auth():
    """分析API认证问题"""

    print("\n🔍 分析API认证问题...")

    # 检查token文件
    token_file = "/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token"
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        print(f"✅ 找到token文件: {token[:10]}...")
    else:
        print("❌ token文件不存在")
        return

    # 测试不同认证方式
    import subprocess

    test_urls = [
        ("http://localhost:3000/api/health", "3000端口健康检查"),
        ("http://localhost:8080/health", "8080端口健康检查"),
        ("http://localhost:3000/", "3000端口根路径"),
        ("http://localhost:8080/", "8080端口根路径"),
    ]

    auth_methods = [
        ("", "无认证"),
        (f"-H 'Authorization: Bearer {token}'", "Bearer Token"),
        (f"-H 'X-API-Key: {token}'", "X-API-Key"),
        (f"-H 'APIKEY: {token}'", "APIKEY头"),
        (f"?apikey={token}", "查询参数apikey"),
        (f"?token={token}", "查询参数token"),
    ]

    for url, desc in test_urls:
        print(f"\n📡 测试 {desc} ({url}):")

        for auth, auth_desc in auth_methods:
            if auth.startswith("?"):
                test_url = f"{url}{auth}"
                cmd = f"curl -s '{test_url}'"
            else:
                cmd = f"curl -s {auth} '{url}'"

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                output = result.stdout[:100].replace("\n", " ")
                if result.returncode == 0:
                    print(f"  {auth_desc}: {output}")
                else:
                    print(f"  {auth_desc}: 错误 (code: {result.returncode})")
            except subprocess.TimeoutExpired:
                print(f"  {auth_desc}: 超时")
            except Exception as e:
                print(f"  {auth_desc}: 异常 - {str(e)}")


def check_current_monitor_config():
    """检查当前监控配置"""

    print("\n🔍 检查当前监控配置状态...")

    # 检查端口监听状态
    import subprocess

    print("端口监听状态:")
    cmd = "netstat -an | grep -E '3000|8080' | grep LISTEN"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line:
                print(f"  {line}")
    except Exception as e:
        print(f"  检查失败: {e}")

    # 检查监控脚本中的端口配置
    print("\n监控脚本端口配置:")
    monitor_scripts = [
        "/Volumes/1TB-M2/openclaw/monitor_web_queue_sync.sh",
        "/Volumes/1TB-M2/openclaw/monitor_all_queues_protection.sh",
    ]

    for script in monitor_scripts:
        if os.path.exists(script):
            with open(script) as f:
                content = f.read()

            port_3000 = ":3000" in content
            port_8080 = ":8080" in content

            status = "❌ 需要修复" if port_3000 else "✅ 正常" if port_8080 else "ℹ️ 无端口配置"
            print(f"  {os.path.basename(script)}: {status}")

            if port_3000:
                # 显示相关行
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if ":3000" in line:
                        print(f"    第{i + 1}行: {line.strip()[:80]}...")


def main():
    """主函数"""

    print("=" * 60)
    print("多Agent系统监控配置修复工具")
    print("=" * 60)

    # 检查当前配置
    check_current_monitor_config()

    # 修复端口配置
    fix_monitor_ports()

    # 分析API认证问题
    analyze_api_auth()

    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

    # 验证修复结果
    print("\n🔍 验证修复结果:")

    # 检查修复后的配置
    check_current_monitor_config()

    print("\n🎉 监控配置修复完成！")
    print("\n下一步建议:")
    print("1. 运行监控脚本测试: bash /Volumes/1TB-M2/openclaw/monitor_web_queue_sync.sh")
    print("2. 检查API端点可用性")
    print("3. 验证队列状态同步")


if __name__ == "__main__":
    main()
