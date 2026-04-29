#!/usr/bin/env python3
"""Test preflight gate for build lane."""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from athena_ai_plan_runner import validate_build_preflight


def test_negative_path_wide_plan() -> None:
    """宽泛策划文档应被拦截并降级为 manual_hold."""
    instruction_text = """#  OpenHuman-Athena 全栈重构策划方案

## 背景
本项目需要彻底重构整个架构，涉及 12 个模块、3 个数据源、5 个外部集成。

## 目标
- 重写所有 API 端点
- 迁移数据库 schema
- 更新前端框架
- 集成第三方服务
- 编写完整测试套件

## 实施步骤
1. 第一阶段：设计新架构
2. 第二阶段：逐个模块替换
3. 第三阶段：集成测试

## 验收标准
项目完成后所有功能正常运行。
"""
    ok, reason, manual = validate_build_preflight(instruction_text, None)
    assert not ok, "宽泛策划文档应被拦截"
    assert manual, "应降级为 manual_hold"
    print(f"✓ 负路径测试通过：{reason}")


def test_negative_path_many_targets() -> None:
    """引用过多目标路径应被拦截."""
    instruction_text = """# 多文件修改任务

需要修改以下文件：
/Volumes/1TB-M2/openclaw/scripts/file1.py
/Volumes/1TB-M2/openclaw/scripts/file2.py
/Volumes/1TB-M2/openclaw/scripts/file3.py
/Volumes/1TB-M2/openclaw/scripts/file4.py
/Volumes/1TB-M2/openclaw/scripts/file5.py
/Volumes/1TB-M2/openclaw/scripts/file6.py
/Volumes/1TB-M2/openclaw/scripts/file7.py
/Volumes/1TB-M2/openclaw/scripts/file8.py
/Volumes/1TB-M2/openclaw/scripts/file9.py

## 验收标准
所有文件修改正确。
"""
    ok, reason, manual = validate_build_preflight(instruction_text, None, max_targets=5)
    assert not ok, "目标文件过多应被拦截"
    assert "超过窄任务上限" in reason
    print(f"✓ 目标过多测试通过：{reason}")


def test_negative_path_missing_acceptance() -> None:
    """缺少验收标准应被拦截."""
    instruction_text = """# 修改某个函数

把函数 foo 改成 bar。

## 步骤
1. 打开文件
2. 修改函数
3. 保存
"""
    ok, reason, manual = validate_build_preflight(instruction_text, None, require_acceptance=True)
    assert not ok, "缺少验收标准应被拦截"
    assert "验收标准" in reason
    print(f"✓ 缺少验收标准测试通过：{reason}")


def test_positive_path_narrow_task() -> None:
    """窄任务应正常放行."""
    instruction_text = """# 修复 scripts/openclaw_roots.py 中的路径错误

## 问题
第 25 行的路径引用错误，应改为正确路径。

## 修改文件
/Volumes/1TB-M2/openclaw/scripts/openclaw_roots.py

## 具体修改
将 `PLAN_CONFIG_PATH` 的默认值从旧路径更新为新路径。

## 验收标准
- 脚本能正常导入
- 路径解析正确
- 单元测试通过
"""
    ok, reason, manual = validate_build_preflight(instruction_text, None)
    assert ok, f"窄任务应通过预检：{reason}"
    assert not manual, "不应降级为 manual_hold"
    print(f"✓ 正路径测试通过：{reason}")


def test_entry_stage_mismatch() -> None:
    """entry_stage 不是 build 应降级."""
    item = {
        "id": "test",
        "title": "审计任务",
        "entry_stage": "review",
        "risk_level": "medium",
    }
    instruction_text = "# 审计任务"
    ok, reason, manual = validate_build_preflight(instruction_text, item)
    assert not ok, "entry_stage 不匹配应被拦截"
    assert manual, "应降级为 manual_hold"
    print(f"✓ entry_stage 检查通过：{reason}")


def test_high_risk() -> None:
    """高风险任务应降级."""
    item = {
        "id": "test",
        "title": "高风险构建",
        "entry_stage": "build",
        "risk_level": "high",
    }
    instruction_text = "# 高风险任务"
    ok, reason, manual = validate_build_preflight(instruction_text, item)
    assert not ok, "高风险任务应被拦截"
    assert manual, "应降级为 manual_hold"
    print(f"✓ 高风险检查通过：{reason}")


def main() -> None:
    """运行所有预检门禁测试."""
    tests = [
        test_negative_path_wide_plan,
        test_negative_path_many_targets,
        test_negative_path_missing_acceptance,
        test_positive_path_narrow_task,
        test_entry_stage_mismatch,
        test_high_risk,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ 测试失败：{test.__name__}: {e}")
            sys.exit(1)
    print("\n所有预检门禁测试通过！")


if __name__ == "__main__":
    main()
