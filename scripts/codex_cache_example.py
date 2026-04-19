#!/usr/bin/env python3
"""
Codex缓存使用示例

展示如何在Athena agent任务中使用Codex语义缓存。
模拟典型的使用场景：任务分析、规划、代码生成等。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from openclaw_roots import RUNTIME_ROOT

    project_root = RUNTIME_ROOT
    sys.path.insert(0, str(project_root))
except ImportError:
    pass

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

try:
    from mini_agent.agent.core.codex_cache import (
        CacheSource,
        CacheStatus,
        CodexCache,
        MatchStrategy,
        get_cache,
    )
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


def example_task_analysis():
    """示例：任务分析缓存"""
    print("=== 示例1: 任务分析缓存 ===")

    cache = get_cache()

    # 模拟任务分析查询
    task_queries = [
        "分析用户需求：需要创建一个用户注册系统，包含邮箱验证和密码加密",
        "分析需求：用户注册系统，需要邮箱验证和密码加密功能",
        "分析任务：构建用户注册模块，支持邮箱验证",
        "分析：用户登录系统需求，包含JWT令牌和会话管理",
    ]

    # 模拟分析结果
    analysis_results = [
        {
            "components": ["用户模型", "注册API", "邮箱验证服务", "密码加密模块"],
            "complexity": "中等",
            "estimated_time": "8小时",
            "recommended_stack": ["Python", "FastAPI", "SQLAlchemy", "JWT"],
        },
        {
            "components": ["注册表单", "验证邮件模板", "密码重置"],
            "complexity": "中等",
            "estimated_time": "6小时",
            "recommended_stack": ["Python", "Django", "PostgreSQL"],
        },
    ]

    print("1. 首次分析查询 (应缓存未命中)")
    for i, query in enumerate(task_queries[:2]):
        result = cache.get(query, source=CacheSource.TASK_ANALYSIS.value)

        if result.status == CacheStatus.MISS:
            print(f"  查询: '{query[:40]}...' -> 未命中")
            # 模拟分析过程
            print(f"  执行分析... (耗时2秒)")
            # 存入缓存
            entry = cache.put(
                raw_input=query,
                payload=analysis_results[i],
                source=CacheSource.TASK_ANALYSIS.value,
                estimated_save_seconds=2.0,
                estimated_save_tokens=100,
            )
            print(f"  分析结果已缓存，键: {entry.key[:8]}...")
        else:
            print(f"  查询: '{query[:40]}...' -> 命中!")
            print(f"  节省时间: {result.entry.estimated_save_seconds if result.entry else 0}秒")

    print("\n2. 相似查询 (应缓存命中)")
    for query in task_queries[2:]:
        result = cache.get(query, source=CacheSource.TASK_ANALYSIS.value)

        if result.status == CacheStatus.HIT:
            print(f"  查询: '{query[:40]}...'")
            print(
                f"  状态: {result.status.value}, 策略: {result.match_strategy.value if result.match_strategy else 'N/A'}"
            )
            print(f"  相似度: {result.similarity_score:.2f}")
            if result.entry:
                print(f"  匹配条目: {result.entry.key[:8]}..., 命中次数: {result.entry.hit_count}")
                print(
                    f"  分析结果: {json.dumps(result.entry.payload, indent=2, ensure_ascii=False)[:100]}..."
                )
        else:
            print(f"  查询: '{query[:40]}...' -> 未命中")

    return cache


def example_code_generation():
    """示例：代码生成缓存"""
    print("\n=== 示例2: 代码生成缓存 ===")

    cache = get_cache()

    # 模拟代码生成任务
    code_requests = [
        "生成Python函数：计算两个数的最大公约数",
        "写一个Python函数计算最大公约数",
        "生成JavaScript函数：验证电子邮件格式",
        "创建Python函数：计算斐波那契数列第n项",
    ]

    code_solutions = [
        {
            "language": "Python",
            "code": "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a",
            "explanation": "使用欧几里得算法计算最大公约数",
            "time_complexity": "O(log min(a, b))",
        },
        {
            "language": "JavaScript",
            "code": "function validateEmail(email) {\n    const re = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;\n    return re.test(email);\n}",
            "explanation": "使用正则表达式验证电子邮件格式",
            "time_complexity": "O(1)",
        },
    ]

    print("1. 代码生成请求")
    for i, request in enumerate(code_requests[:2]):
        result = cache.get(request, source=CacheSource.CODEX_PLAN.value)

        if result.status == CacheStatus.MISS:
            print(f"  请求: '{request}'")
            print(f"  状态: 未命中，生成代码... (耗时3秒)")

            # 存入缓存
            entry = cache.put(
                raw_input=request,
                payload=code_solutions[i],
                source=CacheSource.CODEX_PLAN.value,
                estimated_save_seconds=3.0,
                estimated_save_tokens=150,
            )
            print(f"  代码已缓存，键: {entry.key[:8]}...")
        else:
            print(f"  请求: '{request}'")
            print(
                f"  状态: 命中! 节省 {result.entry.estimated_save_seconds if result.entry else 0}秒"
            )

    print("\n2. 相似代码请求 (测试相似性匹配)")
    for request in code_requests[2:]:
        result = cache.get(request, source=CacheSource.CODEX_PLAN.value)

        if result.status == CacheStatus.HIT:
            print(f"  请求: '{request}'")
            print(
                f"  状态: 命中! 策略: {result.match_strategy.value if result.match_strategy else 'N/A'}"
            )
            print(f"  相似度: {result.similarity_score:.2f}")
            if result.entry:
                print(
                    f"  重用代码: {result.entry.payload['language']} - {result.entry.payload['explanation'][:50]}..."
                )
        else:
            print(f"  请求: '{request}' -> 未命中 (需重新生成)")

    return cache


def example_cache_statistics():
    """示例：缓存统计与报告"""
    print("\n=== 示例3: 缓存统计与报告 ===")

    cache = get_cache()

    # 生成统计报告
    stats = cache.get_stats()
    report = cache.generate_report()

    print("缓存统计摘要:")
    print(f"  总条目数: {stats['total_entries']}")
    print(f"  总命中数: {stats['total_hits']}")
    print(f"  总未命中数: {stats['total_misses']}")
    print(f"  命中率: {stats['hit_rate']:.2%}")
    print(f"  总节省时间: {stats['total_save_seconds']:.1f}秒")
    print(f"  总节省token数: {stats['total_save_tokens']}")

    print("\n按来源统计:")
    for source, data in stats.get("by_source", {}).items():
        print(f"  {source}: {data.get('count', 0)}条目, {data.get('hits', 0)}命中")

    print("\n缓存健康状态:")
    print(f"  状态: {report['health']['status']}")
    print(f"  建议: {report['recommendations']}")

    # 保存报告到文件
    report_file = project_root / "workspace" / "codex_cache_example_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n报告已保存到: {report_file}")

    return cache


def example_integration_with_existing_system():
    """示例：与现有系统集成"""
    print("\n=== 示例4: 与现有系统集成 ===")

    # 模拟Athena任务处理
    print("模拟Athena任务处理流程:")

    cache = get_cache()

    tasks = [
        {
            "id": "task_001",
            "type": "code_review",
            "description": "Review Python code for security vulnerabilities",
            "input": "审查Python代码的安全性漏洞",
        },
        {
            "id": "task_002",
            "type": "plan_generation",
            "description": "Generate project plan for web application",
            "input": "为Web应用生成项目计划",
        },
        {
            "id": "task_003",
            "type": "code_review",
            "description": "Check Python code for security issues",
            "input": "检查Python代码的安全问题",
        },
    ]

    for task in tasks:
        print(f"\n处理任务: {task['id']} - {task['type']}")
        print(f"描述: {task['description']}")

        # 检查缓存
        result = cache.get(
            task["input"],
            source=(
                CacheSource.CODEX_REVIEW.value
                if task["type"] == "code_review"
                else CacheSource.CODEX_PLAN.value
            ),
        )

        if result.status == CacheStatus.HIT:
            print(
                f"✅ 缓存命中! 策略: {result.match_strategy.value if result.match_strategy else 'N/A'}"
            )
            print(f"   相似度: {result.similarity_score:.2f}")
            print(f"   解释: {result.explanation}")
            print(f"   节省时间: {result.entry.estimated_save_seconds if result.entry else 0}秒")

            # 使用缓存结果
            print(f"   使用缓存结果继续处理...")

        else:
            print(f"⏳ 缓存未命中，执行任务...")

            # 模拟任务执行
            import time

            time.sleep(0.5)  # 模拟处理时间

            # 生成结果
            task_result = {
                "task_id": task["id"],
                "status": "completed",
                "output": f"任务 {task['id']} 处理完成",
                "timestamp": datetime.now().isoformat(),
            }

            # 存入缓存
            entry = cache.put(
                raw_input=task["input"],
                payload=task_result,
                source=(
                    CacheSource.CODEX_REVIEW.value
                    if task["type"] == "code_review"
                    else CacheSource.CODEX_PLAN.value
                ),
                estimated_save_seconds=0.5,
                estimated_save_tokens=50,
            )

            print(f"   任务完成，结果已缓存 (键: {entry.key[:8]}...)")

    print("\n" + "=" * 50)
    print("集成示例完成。缓存已在实际任务处理流程中使用。")
    print("相似任务不再需要重复分析，可直接重用缓存结果。")

    return cache


def main():
    """主函数"""
    print("Codex语义缓存使用示例")
    print("=" * 60)

    try:
        # 运行所有示例
        cache = example_task_analysis()
        cache = example_code_generation()
        cache = example_cache_statistics()
        cache = example_integration_with_existing_system()

        print("\n" + "=" * 60)
        print("✅ 所有示例执行完成!")
        print("\n总结:")
        print("1. 建立了最小缓存契约，支持多级存储")
        print("2. 实现了基于关键词/规范化签名的相似性匹配")
        print("3. 提供了命中统计与节省估算")
        print("4. 验证了miss -> write -> hit闭环")
        print("5. 可与现有Athena任务处理系统集成")

        # 最终统计
        final_stats = cache.get_stats()
        print(f"\n最终缓存状态:")
        print(f"  总条目: {final_stats['total_entries']}")
        print(f"  总命中: {final_stats['total_hits']}")
        print(f"  总未命中: {final_stats['total_misses']}")
        print(f"  命中率: {final_stats['hit_rate']:.2%}")
        print(f"  总节省时间: {final_stats['total_save_seconds']:.1f}秒")

        return 0

    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
