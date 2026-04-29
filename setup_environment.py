#!/usr/bin/env python3
"""
环境变量设置脚本 - OpenClaw项目

功能：
1. 检查当前环境变量配置
2. 提供环境变量设置建议
3. 生成shell配置文件代码
4. 验证环境变量设置是否正确

使用说明：
  python3 setup_environment.py          # 检查当前配置
  python3 setup_environment.py --guide  # 显示设置指南
  python3 setup_environment.py --shell  # 生成shell配置文件代码
"""

import argparse
import os
import sys
from pathlib import Path


def check_current_environment():
    """检查当前环境变量配置"""
    print("🔍 环境变量配置检查")
    print("=" * 60)

    env_vars = {
        "OPENCLAW_ROOT": {
            "description": "项目根目录环境变量",
            "required": False,
            "default": "/Volumes/1TB-M2/openclaw",
            "used_by": "config.paths.py, 用于确定项目根目录",
        },
        "ATHENA_RUNTIME_ROOT": {
            "description": "Athena运行时根目录",
            "required": False,
            "default": "/Volumes/1TB-M2/openclaw",
            "used_by": "scripts/openclaw_roots.py, Athena脚本使用的根目录",
        },
        "DASHSCOPE_API_KEY": {
            "description": "DashScope API密钥",
            "required": True,
            "default": None,
            "used_by": "API调用，需要有效密钥",
        },
    }

    results = {}
    for var_name, var_info in env_vars.items():
        current_value = os.environ.get(var_name)
        is_set = current_value is not None and current_value != ""

        results[var_name] = {
            "is_set": is_set,
            "value": current_value if is_set else None,
            "info": var_info,
        }

        status = "✅ 已设置" if is_set else "⚠️  未设置"
        if is_set and var_name in ["DASHSCOPE_API_KEY"]:
            # 对敏感值只显示长度
            print(f"{status} {var_name}: {var_info['description']}")
            print(f"   值长度: {len(current_value)} 字符")
        elif is_set:
            print(f"{status} {var_name}: {var_info['description']}")
            print(f"   当前值: {current_value}")
        else:
            print(f"{status} {var_name}: {var_info['description']}")
            print(f"   默认值: {var_info['default']}")

        print(f"   用途: {var_info['used_by']}")
        print()

    return results


def generate_shell_code(shell_type="bash"):
    """生成shell配置文件代码"""
    print(f"📝 生成 {shell_type} 配置文件代码")
    print("=" * 60)

    project_root = Path(__file__).parent
    default_root = str(project_root)

    if shell_type == "bash" or shell_type == "zsh":
        code = f"""# OpenClaw项目环境变量配置
export OPENCLAW_ROOT="{default_root}"
export ATHENA_RUNTIME_ROOT="{default_root}"

# DashScope API密钥 (需要替换为你的实际密钥)
# export DASHSCOPE_API_KEY="your-dashscope-api-key-here"

# 添加到PATH（可选）
export PATH="$OPENCLAW_ROOT/scripts:$PATH"

# 验证配置
echo "✅ OpenClaw环境变量已配置"
echo "   OPENCLAW_ROOT: $OPENCLAW_ROOT"
echo "   ATHENA_RUNTIME_ROOT: $ATHENA_RUNTIME_ROOT"
"""
    elif shell_type == "fish":
        code = f"""# OpenClaw项目环境变量配置
set -gx OPENCLAW_ROOT "{default_root}"
set -gx ATHENA_RUNTIME_ROOT "{default_root}"

# DashScope API密钥 (需要替换为你的实际密钥)
# set -gx DASHSCOPE_API_KEY "your-dashscope-api-key-here"

# 添加到PATH（可选）
set -gx fish_user_paths $OPENCLAW_ROOT/scripts $fish_user_paths

# 验证配置
echo "✅ OpenClaw环境变量已配置"
echo "   OPENCLAW_ROOT: $OPENCLAW_ROOT"
echo "   ATHENA_RUNTIME_ROOT: $ATHENA_RUNTIME_ROOT"
"""
    else:
        code = f"# 不支持 {shell_type} shell类型"

    print("将以下代码添加到你的shell配置文件中 (~/.bashrc, ~/.zshrc, ~/.config/fish/config.fish):")
    print()
    print(code)
    print()
    print("应用配置:")
    print(f"  source ~/.{shell_type}rc  # 或重启终端")

    return code


def show_setup_guide():
    """显示环境变量设置指南"""
    print("📚 环境变量设置指南")
    print("=" * 60)

    print("""
1. 临时设置（仅当前终端会话）:

   Bash/Zsh:
     export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"
     export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"

   Fish:
     set -gx OPENCLAW_ROOT "/Volumes/1TB-M2/openclaw"
     set -gx ATHENA_RUNTIME_ROOT "/Volumes/1TB-M2/openclaw"

2. 永久设置（添加到shell配置文件）:

   a. 确定你的shell类型:
      echo $SHELL

   b. 编辑对应的配置文件:
      • Bash: ~/.bashrc 或 ~/.profile
      • Zsh: ~/.zshrc
      • Fish: ~/.config/fish/config.fish

   c. 添加环境变量定义（使用--shell选项生成代码）

3. 验证设置:

   运行此脚本检查配置:
     python3 setup_environment.py

   或手动检查:
     echo $OPENCLAW_ROOT
     echo $ATHENA_RUNTIME_ROOT

4. 重要说明:

   • OPENCLAW_ROOT: 用于config.paths.py模块，所有Python脚本应使用此变量
   • ATHENA_RUNTIME_ROOT: 用于scripts/openclaw_roots.py，Athena脚本使用
   • 建议两个变量设置为相同值，除非有特殊部署需求
   • 设置后需要重启终端或重新加载配置文件

5. 故障排除:

   • 如果脚本仍使用硬编码路径，检查是否导入了正确的路径模块
   • 确保环境变量在Python脚本运行时已设置
   • 对于后台进程，需要确保环境变量传递给子进程
""")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenClaw环境变量设置工具")
    parser.add_argument("--guide", action="store_true", help="显示设置指南")
    parser.add_argument(
        "--shell", type=str, choices=["bash", "zsh", "fish"], help="生成指定shell的配置文件代码"
    )

    args = parser.parse_args()

    print("🚀 OpenClaw环境变量设置工具")
    print("=" * 60)

    if args.guide:
        show_setup_guide()
        return

    if args.shell:
        generate_shell_code(args.shell)
        return

    # 默认行为：检查当前配置
    results = check_current_environment()

    # 总结
    print("🎯 总结与建议")
    print("=" * 60)

    missing_vars = [
        var for var, data in results.items() if not data["is_set"] and data["info"]["required"]
    ]

    if missing_vars:
        print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        print("   运行 --guide 查看设置指南")
        print("   运行 --shell [bash|zsh|fish] 生成配置文件代码")
    else:
        print("✅ 环境变量配置基本正常")

    optional_vars = [
        var for var, data in results.items() if not data["is_set"] and not data["info"]["required"]
    ]

    if optional_vars:
        print(f"💡 建议设置可选环境变量: {', '.join(optional_vars)}")
        print("   这些变量支持灵活部署和配置管理")

    print()
    print("🔧 使用选项:")
    print("  python3 setup_environment.py --guide   # 显示完整设置指南")
    print("  python3 setup_environment.py --shell bash  # 生成bash配置代码")
    print("  python3 setup_environment.py --shell zsh   # 生成zsh配置代码")
    print("  python3 setup_environment.py --shell fish  # 生成fish配置代码")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
