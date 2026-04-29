#!/usr/bin/env python3
"""
Athena CLI - Athena 命令行工具

用于测试 Athena 与 AutoGLM Bridge 的集成
"""

import argparse
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 手动加载 .env 文件
def load_env_file(env_path):
    """手动解析 .env 文件并设置环境变量"""
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_env_file(env_path)

from athena_adapter import run_task
from autoglm_bridge.model_client import check_real_mode_config


def check_config():
    """检查真实模式配置"""
    print("=== 真实模式配置检查 ===")
    print()

    config = check_real_mode_config()

    print("环境变量状态:")
    print(f"  API_KEY: {'✓ 已检测到' if config['env_api_key'] else '✗ 未检测到'}")
    print(f"  BASE_URL: {'✓ 已检测到' if config['env_base_url'] else '✗ 未检测到'}")
    print(
        f"  MODEL: {'✓ ' + os.getenv('AUTOGLM_MODEL', 'gpt-4') if config['env_model'] else '✗ 未检测到'}"
    )
    print()

    print("配置状态:")
    print(f"  环境变量配置完整: {'✓ 是' if config['env_configured'] else '✗ 否'}")
    print(f"  实例配置完整: {'✓ 是' if config['instance_configured'] else '✗ 否'}")
    print()

    print("运行模式:")
    print(f"  默认模式: {config['default_mode']}")
    print(f"  当前模式: {config['current_mode']}")
    print()

    if not config["env_configured"]:
        print("⚠️  真实模式未配置完整，无法使用 --real 模式")
        print("请复制 .env.example 为 .env 并填写配置")
        return False
    else:
        print("✓ 真实模式配置完整，可以使用 --real 模式")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Athena Agent CLI - 手机控制任务执行")

    parser.add_argument("task", type=str, nargs="?", default="打开设置", help="要执行的任务描述")

    parser.add_argument("--device", type=str, default="zflip3", help="目标设备 (默认: zflip3)")

    parser.add_argument("--max-steps", type=int, default=10, help="最大执行步数 (默认: 10)")

    parser.add_argument(
        "--mock", action="store_true", default=True, help="使用 mock 模式 (默认: True)"
    )

    parser.add_argument("--real", action="store_true", help="使用真实模式 (需要配置 API)")

    parser.add_argument("--check-real-config", action="store_true", help="检查真实模式配置状态")

    parser.add_argument("--output", type=str, help="输出结果到文件")

    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 检查配置模式
    if args.check_real_config:
        check_config()
        sys.exit(0)

    # 确定使用 mock 还是真实模式
    use_mock = not args.real

    # 如果用户要求使用真实模式，检查配置
    if args.real:
        config = check_real_mode_config()
        if not config["env_configured"]:
            print("错误: 真实模式未配置完整")
            print("请先运行: python run_athena.py --check-real-config")
            print("或编辑 .env 文件配置 API")
            sys.exit(1)

    if args.verbose:
        print("=== Athena CLI ===")
        print(f"任务: {args.task}")
        print(f"设备: {args.device}")
        print(f"最大步数: {args.max_steps}")
        print(f"模式: {'MOCK' if use_mock else 'REAL'}")
        print()

    # 执行任务
    print(f"执行任务: {args.task}")
    print("-" * 40)

    result = run_task(
        task=args.task, device=args.device, max_steps=args.max_steps, use_mock=use_mock
    )

    # 输出结果
    print()
    print("=" * 40)
    print("执行结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 保存到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")

    # 返回状态码
    if result.get("success", False):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
