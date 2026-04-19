#!/usr/bin/env python3
"""
MAREF内存管理和Coding审计系统演示
展示如何在实际项目中使用审计系统
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 禁用详细日志以便演示
import logging

logging.getLogger().setLevel(logging.WARNING)

print("=== MAREF Coding审计系统演示 ===\n")


def demo_basic_usage():
    """演示基本用法"""
    print("1. 基本用法演示")
    print("-" * 40)

    from coding_audit_system import CodingAuditSystem, GenerationReason, require_audit

    # 初始化审计系统
    audit_system = CodingAuditSystem()
    print("✅ 初始化审计系统")

    # 注册一个Claude Code智能体
    audit_system.register_agent(
        agent_id="claude_demo_001",
        agent_type="claude_code",
        capabilities=["code_generation", "refactoring"],
    )
    print("✅ 注册Claude Code智能体")

    # 方式1: 使用装饰器
    print("\n🔧 方式1: 使用装饰器强制审计")

    @audit_system.audit_decorator("claude_demo_001", "claude_code")
    def generate_python_code(prompt: str, context: dict = None) -> str:
        """模拟Python代码生成"""
        # 实际中这里会调用AI模型
        return f"""# 生成的Python代码
# 提示: {prompt}
# 基于 {len(context.get('relevant_memories', [])) if context else 0} 条相关记忆

import os
import json

def process_data(data):
    '''处理数据函数'''
    if not data:
        return None

    # 计算统计
    stats = {{
        "count": len(data),
        "sum": sum(data),
        "average": sum(data) / len(data) if data else 0
    }}

    return stats

if __name__ == "__main__":
    # 示例数据
    sample_data = [1, 2, 3, 4, 5]
    result = process_data(sample_data)
    print(f"结果: {{result}}")
"""

    # 生成代码（自动审计）
    code = generate_python_code(
        prompt="创建一个数据处理函数",
        project_path="/demo/project",
        file_path="/demo/project/data_processor.py",
    )

    print(f"✅ 生成代码成功 ({len(code)} 字符)")
    print(f"   前3行: {'\\n'.join(code.split('\\n')[:3])}")

    # 方式2: 使用上下文管理器
    print("\n🔧 方式2: 使用上下文管理器")

    with audit_system.audit_context(
        agent_id="claude_demo_001",
        agent_type="claude_code",
        project_path="/demo/project",
        file_path="/demo/project/utils.py",
        prompt="创建一个工具函数集合",
    ) as ctx:

        def custom_generator(prompt: str, context: dict) -> str:
            mem_count = len(context.get("relevant_memories", []))
            return f"""# 工具函数集合
# 基于 {mem_count} 条相关记忆生成

import datetime
import hashlib

def get_timestamp():
    '''获取当前时间戳'''
    return datetime.datetime.now().isoformat()

def generate_hash(data: str) -> str:
    '''生成数据哈希'''
    return hashlib.sha256(data.encode()).hexdigest()

def format_output(data, indent=2):
    '''格式化输出'''
    import json
    return json.dumps(data, indent=indent, ensure_ascii=False)
"""

        utils_code = ctx.generate(custom_generator)
        print(f"✅ 工具函数生成成功 ({len(utils_code)} 字符)")
        print(f"   上下文查询ID: {ctx.context_query_id}")

    return True


def demo_multi_platform():
    """演示多平台适配"""
    print("\n\n2. 多平台适配器演示")
    print("-" * 40)

    from coding_audit_system import CodingAuditSystem

    audit_system = CodingAuditSystem()

    # Claude Code适配器
    print("\n🔧 Claude Code适配器")
    claude_adapter = audit_system.create_claude_code_adapter("claude_demo")

    @claude_adapter
    def claude_generate(prompt: str, context: dict = None) -> str:
        return f"# Claude生成的代码\n# {prompt}"

    code1 = claude_generate(
        prompt="测试Claude适配器", project_path="/demo/multi", file_path="/demo/multi/claude.py"
    )
    print(f"✅ Claude适配器: {len(code1)} 字符")

    # trae cn适配器（中文环境）
    print("\n🔧 trae cn适配器（中文环境）")
    trae_adapter = audit_system.create_trae_cn_adapter("trae_demo")

    @trae_adapter
    def trae_generate(prompt: str, context: dict = None) -> str:
        return f"# trae cn生成的代码（中文）\n# 提示: {prompt}\nprint('你好，世界！')"

    code2 = trae_generate(
        prompt="测试trae cn适配器", project_path="/demo/multi", file_path="/demo/multi/trae.py"
    )
    print(f"✅ trae cn适配器: {len(code2)} 字符")

    # VSCode适配器（模拟）
    print("\n🔧 VSCode适配器（模拟API）")
    vscode_adapter = audit_system.create_vscode_adapter("vscode_demo")

    code3, _, _ = vscode_adapter.generate_with_audit(
        prompt="测试VSCode智能提示", file_path="/demo/multi/vscode.js", project_path="/demo/multi"
    )
    print(f"✅ VSCode适配器: {len(code3)} 字符")

    return True


def demo_audit_trail():
    """演示审计追踪和回滚"""
    print("\n\n3. 审计追踪和回滚演示")
    print("-" * 40)

    from coding_audit_system import CodingAuditSystem

    # 创建测试审计系统
    test_db = Path(__file__).parent / "demo_audit.db"
    if test_db.exists():
        test_db.unlink()

    audit_system = CodingAuditSystem(db_path=str(test_db))

    # 注册测试agent
    audit_system.register_agent(
        agent_id="demo_agent", agent_type="demo", capabilities=["code_generation"]
    )

    # 生成一些测试审计记录
    @audit_system.audit_decorator("demo_agent", "demo")
    def demo_generator(prompt: str, context: dict = None) -> str:
        return f"# 演示代码\n# {prompt}"

    print("生成测试审计记录...")
    for i in range(3):
        demo_generator(
            prompt=f"测试记录 {i+1}",
            project_path="/demo/audit",
            file_path=f"/demo/audit/file_{i+1}.py",
        )

    # 查询审计追踪
    print("\n📋 查询审计追踪:")
    trail = audit_system.get_audit_trail(project_path="/demo/audit", hours=24, limit=5)

    print(f"找到 {len(trail)} 条审计记录:")
    for i, entry in enumerate(trail, 1):
        print(f"  {i}. [{entry['timestamp'][11:19]}] {entry['agent_id']}")
        print(f"      文件: {entry['file_path']}")
        print(f"      原因: {entry['generation_reason']}")

    # 清理
    if test_db.exists():
        test_db.unlink()

    return True


def demo_maref_integration():
    """演示与MAREF系统的集成"""
    print("\n\n4. MAREF系统集成演示")
    print("-" * 40)

    try:
        from coding_audit_system import CodingAuditSystem
        from maref_memory_integration import (
            init_memory_manager,
            record_agent_action,
            record_cognitive_alignment_event,
            record_system_event,
        )

        print("初始化MAREF内存管理器...")
        memory_manager = init_memory_manager()

        # 创建与MAREF集成的审计系统
        audit_system = CodingAuditSystem(memory_manager=memory_manager)

        # 记录系统事件
        print("记录系统事件...")
        event_id = record_system_event(
            event_type="demo_integration",
            event_data={"phase": "demo", "timestamp": "2026-04-14"},
            severity="info",
            source="demo_script",
        )
        print(f"✅ 系统事件记录ID: {event_id}")

        # 记录认知对齐事件
        print("记录认知对齐事件...")
        alignment_id = record_cognitive_alignment_event(
            alignment_type="demo_alignment",
            involved_agents=["coordinator", "executor", "memory"],
            alignment_data={"demo": True},
            alignment_result={"success": True, "aligned_agents": 3},
        )
        print(f"✅ 认知对齐事件ID: {alignment_id}")

        # 使用装饰器记录智能体行动
        class DemoAgent:
            agent_id = "demo_maref_agent"
            agent_type = "maref_integration"

            @record_agent_action(action_type="demo_action")
            def perform_demo(self, param):
                print(f"  📝 执行MAREF集成行动: {param}")
                return {"result": f"action_{param}"}

        agent = DemoAgent()
        result = agent.perform_demo("test_param")
        print(f"✅ 智能体行动结果: {result}")

        # 使用审计系统生成代码（与MAREF内存集成）
        print("\n使用集成审计系统生成代码...")
        audit_system.register_agent(
            agent_id="integrated_agent",
            agent_type="claude_code",
            capabilities=["code_generation", "maref_integration"],
        )

        @audit_system.audit_decorator("integrated_agent", "claude_code")
        def integrated_generator(prompt: str, context: dict = None) -> str:
            return f"# MAREF集成生成的代码\n# 提示: {prompt}"

        code = integrated_generator(
            prompt="测试MAREF集成审计",
            project_path="/demo/integration",
            file_path="/demo/integration/maref_demo.py",
        )

        print(f"✅ 集成代码生成成功: {len(code)} 字符")

        return True

    except ImportError as e:
        print(f"⚠️  无法导入MAREF模块: {e}")
        return False


def main():
    """主演示函数"""
    print("🚀 开始演示MAREF Coding审计系统")
    print("=" * 50)

    try:
        # 运行所有演示
        demo_basic_usage()
        demo_multi_platform()
        demo_audit_trail()
        demo_maref_integration()

        print("\n" + "=" * 50)
        print("🎉 演示完成！")
        print("\n主要功能总结:")
        print("1. ✅ 强制审计 - 所有代码生成自动记录")
        print("2. ✅ 记忆查询 - 生成前查询相关记忆确保认知对齐")
        print("3. ✅ 多平台支持 - Claude Code、VSCode、trae cn等")
        print("4. ✅ 完整追溯 - 审计追踪和代码回滚")
        print("5. ✅ MAREF集成 - 与现有MAREF内存系统无缝集成")
        print("6. ✅ 非侵入式 - 装饰器和包装器模式，无需修改现有代码")

        return True

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
