"""
任务宽度治理集成脚本
将任务宽度治理集成到Athena任务编排流程中
"""

import sys
from pathlib import Path

# 添加scripts目录到Python路径
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from task_width_governance import TaskWidthGovernance


def integrate_with_athena():
    """与Athena系统集成"""
    governor = TaskWidthGovernance()

    print("任务宽度治理模块已成功集成到Athena系统")
    print("主要功能:")
    print("1. 自动任务复杂度分析")
    print("2. 智能任务分解建议")
    print("3. 防止过宽任务阻塞队列")
    print("4. 提高任务执行成功率")

    return governor


def preprocess_task_for_athena(task_description: str):
    """为Athena预处理任务"""
    governor = TaskWidthGovernance()

    # 分析任务
    analysis = governor.analyze_task(task_description)

    print("任务分析结果:")
    print(f"  描述: {task_description[:100]}...")
    print(f"  复杂度分数: {analysis.complexity_score}")
    print(f"  级别: {analysis.complexity_level.value}")
    print(f"  估算时间: {analysis.estimated_time_seconds // 60}分钟")

    # 检查是否需要分解
    if governor.should_decompose_task(analysis):
        print("  ⚠️ 任务过宽，建议分解")
        print(f"  分解建议: {analysis.decomposition_suggestions}")

        # 生成分解计划
        decomposition_plan = governor.create_decomposition_plan(task_description, analysis)
        print(f"  分解计划 ({len(decomposition_plan)}个子任务):")
        for subtask in decomposition_plan:
            print(f"    - {subtask['description']} (优先级: {subtask['priority']})")

        return {
            "needs_decomposition": True,
            "analysis": analysis.to_dict(),
            "decomposition_plan": decomposition_plan,
        }
    else:
        print("  ✅ 任务宽度合适，可直接执行")
        return {
            "needs_decomposition": False,
            "analysis": analysis.to_dict(),
            "decomposition_plan": [],
        }


if __name__ == "__main__":
    # 测试集成
    test_task = (
        "实现完整的用户管理系统，包括用户注册、登录、权限管理、个人资料编辑、密码重置和账户删除功能"
    )
    result = preprocess_task_for_athena(test_task)

    print("\n集成测试完成!")
    print(f"任务需要分解: {result['needs_decomposition']}")
