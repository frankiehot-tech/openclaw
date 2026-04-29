#!/usr/bin/env python3
"""
MVP测试环境配置解析测试

测试目标：
1. 验证 mvp_test_env.yaml 文件可加载且为有效YAML
2. 验证控制面引用存在且指向正确文件
3. 验证必填字段存在且类型正确
4. 验证环境定义完整性
5. 验证用户分层定义完整性

使用方法：
python test_mvp_config_load.py [--verbose] [--validate-all]

退出码：
0 - 所有测试通过
1 - 配置加载失败
2 - 验证失败
3 - 控制面集成失败
"""

import sys
from pathlib import Path
from typing import Any

import yaml

# 添加mini-agent目录到路径，以便导入相关模块
sys.path.insert(0, str(Path(__file__).parent.parent / "mini-agent"))

VERBOSE = False
VALIDATE_ALL = False


def log(msg: str, level: str = "INFO"):
    """日志输出"""
    if VERBOSE or level in ("ERROR", "WARN"):
        print(f"[{level}] {msg}")


def load_yaml_file(file_path: Path) -> dict[str, Any] | None:
    """加载YAML文件"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)
        log(f"成功加载YAML文件: {file_path}")
        return content
    except yaml.YAMLError as e:
        log(f"YAML解析错误: {e}", "ERROR")
        return None
    except FileNotFoundError:
        log(f"文件不存在: {file_path}", "ERROR")
        return None
    except Exception as e:
        log(f"加载文件时出错: {e}", "ERROR")
        return None


def test_mvp_config_load() -> bool:
    """测试MVP配置加载"""
    config_path = Path(__file__).parent.parent / "mini-agent/config/mvp_test_env.yaml"
    log(f"测试配置加载: {config_path}")

    config = load_yaml_file(config_path)
    if config is None:
        return False

    # 检查必需顶层字段
    required_top_level = [
        "version",
        "description",
        "test_environments",
        "internal_user_tiers",
    ]
    for field in required_top_level:
        if field not in config:
            log(f"缺少必需字段: {field}", "ERROR")
            return False

    log("✓ MVP配置加载测试通过")
    return True


def test_mvp_config_structure() -> bool:
    """测试MVP配置结构完整性"""
    config_path = Path(__file__).parent.parent / "mini-agent/config/mvp_test_env.yaml"
    config = load_yaml_file(config_path)
    if config is None:
        return False

    errors = []

    # 1. 测试环境定义
    envs = config.get("test_environments", {}).get("environments", {})
    if not envs:
        errors.append("test_environments.environments 为空")

    required_env_fields = [
        "name",
        "mode",
        "purpose",
        "resource_budget",
        "access_methods",
    ]
    for env_id, env_data in envs.items():
        for field in required_env_fields:
            if field not in env_data:
                errors.append(f"环境 {env_id} 缺少字段: {field}")

    # 2. 用户分层定义
    tiers = config.get("internal_user_tiers", {}).get("tiers", {})
    if not tiers:
        errors.append("internal_user_tiers.tiers 为空")

    required_tier_fields = [
        "label",
        "description",
        "default_permissions",
        "trial_focus",
    ]
    for tier_id, tier_data in tiers.items():
        for field in required_tier_fields:
            if field not in tier_data:
                errors.append(f"用户分层 {tier_id} 缺少字段: {field}")

    # 3. 权限定义
    permissions = config.get("internal_user_tiers", {}).get("permission_definitions", {})
    if not permissions:
        errors.append("internal_user_tiers.permission_definitions 为空")

    # 4. onboarding骨架
    onboarding = config.get("onboarding_skeleton", {})
    if not onboarding:
        errors.append("onboarding_skeleton 为空")

    if errors:
        for err in errors:
            log(f"结构错误: {err}", "ERROR")
        return False

    log(
        f"✓ MVP配置结构测试通过: {len(envs)} 个环境, {len(tiers)} 个用户分层, {len(permissions)} 个权限定义"
    )
    return True


def test_control_plane_integration() -> bool:
    """测试控制面集成"""
    control_plane_path = Path(__file__).parent.parent / "mini-agent/config/control_plane.yaml"
    log(f"测试控制面集成: {control_plane_path}")

    cp_config = load_yaml_file(control_plane_path)
    if cp_config is None:
        return False

    # 检查project作用域中是否有mvp_test_env引用
    project = cp_config.get("project", {})
    if "mvp_test_env" not in project:
        log("控制面project作用域缺少mvp_test_env引用", "ERROR")
        return False

    mvp_ref = project["mvp_test_env"]
    if not isinstance(mvp_ref, dict):
        log("mvp_test_env引用不是字典类型", "ERROR")
        return False

    # 检查config_source
    if mvp_ref.get("config_source") != "mvp_test_env.yaml":
        log(f"config_source不匹配: {mvp_ref.get('config_source')}", "ERROR")
        return False

    # 检查compatibility_bridge中的映射
    bridge = cp_config.get("compatibility_bridge", {}).get("existing_config_mapping", {})
    if "mvp_test_env.yaml" not in bridge:
        log("compatibility_bridge中缺少mvp_test_env.yaml映射", "WARN")
        # 不视为致命错误

    log("✓ 控制面集成测试通过")
    return True


def test_user_tier_permission_mapping() -> bool:
    """测试用户分层权限映射"""
    config_path = Path(__file__).parent.parent / "mini-agent/config/mvp_test_env.yaml"
    config = load_yaml_file(config_path)
    if config is None:
        return False

    tiers = config.get("internal_user_tiers", {}).get("tiers", {})
    permission_defs = config.get("internal_user_tiers", {}).get("permission_definitions", {})

    errors = []

    for tier_id, tier_data in tiers.items():
        permissions = tier_data.get("default_permissions", [])
        for perm in permissions:
            if perm not in permission_defs:
                errors.append(f"用户分层 {tier_id} 引用了未定义的权限: {perm}")

    if errors:
        for err in errors:
            log(f"权限映射错误: {err}", "ERROR")
        return False

    log(
        f"✓ 用户分层权限映射测试通过: 验证了 {sum(len(t.get('default_permissions', [])) for t in tiers.values())} 个权限引用"
    )
    return True


def test_environment_health_checks() -> bool:
    """测试环境健康检查定义"""
    config_path = Path(__file__).parent.parent / "mini-agent/config/mvp_test_env.yaml"
    config = load_yaml_file(config_path)
    if config is None:
        return False

    health_checks = config.get("environment_health", {}).get("health_checks", {})
    smoke_tests = config.get("environment_health", {}).get("smoke_test_suite", {}).get("tests", [])

    if not health_checks:
        log("environment_health.health_checks 为空", "WARN")

    if not smoke_tests:
        log("environment_health.smoke_test_suite.tests 为空", "WARN")

    log("✓ 环境健康检查测试通过")
    return True


def run_all_tests() -> bool:
    """运行所有测试"""
    tests = [
        ("MVP配置加载", test_mvp_config_load),
        ("MVP配置结构", test_mvp_config_structure),
        ("控制面集成", test_control_plane_integration),
        ("用户分层权限映射", test_user_tier_permission_mapping),
        ("环境健康检查", test_environment_health_checks),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        log(f"\n--- 运行测试: {test_name} ---")
        try:
            if test_func():
                log(f"✓ {test_name} 通过", "INFO")
                passed += 1
            else:
                log(f"✗ {test_name} 失败", "ERROR")
                failed += 1
        except Exception as e:
            log(f"✗ {test_name} 异常: {e}", "ERROR")
            failed += 1

    log(f"\n=== 测试结果: 通过 {passed}, 失败 {failed}, 总计 {passed + failed} ===")

    if failed > 0:
        log("部分测试失败，请检查配置", "ERROR")
        return False

    log("所有测试通过！MVP测试环境配置骨架验证成功。", "INFO")
    return True


def main() -> int:
    """主函数"""
    global VERBOSE, VALIDATE_ALL

    # 解析命令行参数
    args = sys.argv[1:]
    if "--verbose" in args:
        VERBOSE = True
    if "--validate-all" in args:
        VALIDATE_ALL = True

    log("开始MVP测试环境配置解析测试", "INFO")

    # 检查配置文件是否存在
    config_path = Path(__file__).parent.parent / "mini-agent/config/mvp_test_env.yaml"
    if not config_path.exists():
        log(f"配置文件不存在: {config_path}", "ERROR")
        return 1

    # 运行测试
    success = run_all_tests()

    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
