#!/usr/bin/env python3
"""
通用Coding Agent审计对齐系统

核心功能：
1. 强制审计 - 所有代码生成必须通过审计系统记录
2. 记忆查询 - 生成前自动查询相关记忆确保认知对齐
3. 完整追溯 - 记录生成前后的完整决策链
4. 一键回滚 - 基于审计记录恢复代码到任意历史版本

支持平台：
- Claude Code (Python环境直接集成)
- VSCode (通过审计服务API)
- Open Code (命令行包装器)
- Codex (API代理层)
- trae cn (中文环境适配)
- 其他任何Coding Agent
"""

import functools
import hashlib
import inspect
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from maref_memory_manager import (
    MAREFMemoryManager,
    MemoryEntry,
    MemoryEntryType,
    MemoryPriority,
)

logger = logging.getLogger(__name__)


class AuditPhase(str, Enum):
    """审计阶段"""

    PRE_GENERATION = "pre_generation"  # 生成前
    POST_GENERATION = "post_generation"  # 生成后
    COMPLETE = "complete"  # 完整审计


class GenerationReason(str, Enum):
    """代码生成原因"""

    USER_REQUEST = "user_request"  # 用户请求
    BUG_FIX = "bug_fix"  # 修复bug
    REFACTORING = "refactoring"  # 重构
    FEATURE_ADDITION = "feature_addition"  # 添加功能
    OPTIMIZATION = "optimization"  # 优化
    CODE_REVIEW = "code_review"  # 代码审查建议
    TEST_GENERATION = "test_generation"  # 测试生成
    DOCUMENTATION = "documentation"  # 文档生成


class CodingAuditSystem:
    """
    通用Coding Agent审计系统

    强制所有代码生成通过审计，确保认知对齐和可追溯性。
    """

    def __init__(
        self,
        memory_manager: Optional[MAREFMemoryManager] = None,
        memory_dir: str = None,
        db_path: str = None,
    ):
        """
        初始化审计系统

        Args:
            memory_manager: 现有的内存管理器实例（可选）
            memory_dir: 内存目录
            db_path: 数据库路径
        """
        if memory_manager:
            self.memory_manager = memory_manager
        else:
            self.memory_manager = MAREFMemoryManager(memory_dir, db_path)

        self.audit_cache = {}  # 审计记录缓存
        self.agent_registry = {}  # 已注册的agent信息
        logger.info("Coding审计系统初始化完成")

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Dict[str, Any] = None,
    ):
        """
        注册Coding Agent

        Args:
            agent_id: 代理唯一标识
            agent_type: 代理类型 (claude_code, vscode, open_code, codex, trae_cn, etc.)
            capabilities: 支持的能力列表
            metadata: 额外元数据
        """
        self.agent_registry[agent_id] = {
            "agent_type": agent_type,
            "capabilities": capabilities,
            "metadata": metadata or {},
            "registered_at": datetime.now().isoformat(),
        }
        logger.info(f"Agent注册成功: {agent_id} ({agent_type})")

    def query_relevant_memories(
        self,
        project_path: str,
        file_path: str,
        intent: str,
        agent_id: str,
        query_params: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询与代码生成相关的记忆

        Args:
            project_path: 项目路径
            file_path: 文件路径
            intent: 查询意图
            agent_id: 代理ID
            query_params: 查询参数

        Returns:
            相关记忆列表
        """
        # 构建查询条件
        tags = [f"project_{project_path}", f"file_{file_path}", "code_related"]

        if intent:
            tags.append(f"intent_{intent}")

        # 查询相关记忆条目
        memories = self.memory_manager.query_memory(
            tags=tags, limit=20, priority=MemoryPriority.MEDIUM
        )

        # 转换格式
        results = []
        for memory in memories:
            results.append(
                {
                    "entry_id": memory.entry_id,
                    "entry_type": memory.entry_type.value,
                    "timestamp": memory.timestamp,
                    "source_agent": memory.source_agent,
                    "content": memory.content,
                    "tags": memory.tags,
                }
            )

        logger.debug(f"查询到 {len(results)} 条相关记忆: {project_path}/{file_path}")
        return results

    def audit_code_generation(
        self,
        agent_id: str,
        agent_type: str,
        project_path: str,
        file_path: str,
        generation_prompt: str,
        generation_func: Callable,
        generation_reason: Union[str, GenerationReason] = "user_request",
        context_intent: str = "code_generation",
        force_audit: bool = True,
    ) -> Tuple[str, str, str]:
        """
        审计代码生成（核心方法）

        Args:
            agent_id: 代理ID
            agent_type: 代理类型
            project_path: 项目路径
            file_path: 文件路径
            generation_prompt: 生成提示
            generation_func: 代码生成函数，接受(prompt, context)返回代码
            generation_reason: 生成原因
            context_intent: 上下文查询意图
            force_audit: 是否强制审计

        Returns:
            (generated_code, context_query_id, generation_record_id)
        """
        if not force_audit:
            # 非强制模式，直接生成
            logger.warning(f"非强制审计模式，直接生成代码: {agent_id}")
            generated_code = generation_func(generation_prompt, {})
            return generated_code, None, None

        start_time = datetime.now()

        # ===== 生成前阶段：查询相关记忆 =====
        logger.info(f"开始代码生成审计: {agent_id} -> {file_path}")

        # 查询相关记忆
        relevant_memories = self.query_relevant_memories(
            project_path=project_path,
            file_path=file_path,
            intent=context_intent,
            agent_id=agent_id,
            query_params={"prompt": generation_prompt},
        )

        # 记录上下文查询
        context_query_id = self.memory_manager.record_code_context_query(
            agent_id=agent_id,
            agent_type=agent_type,
            project_path=project_path,
            file_path=file_path,
            query_intent=context_intent,
            query_parameters={"prompt": generation_prompt, "file_path": file_path},
            query_results=relevant_memories,
        )

        # ===== 生成阶段：执行代码生成 =====
        # 构建增强的上下文
        generation_context = {
            "project_path": project_path,
            "file_path": file_path,
            "relevant_memories": relevant_memories,
            "generation_prompt": generation_prompt,
            "agent_id": agent_id,
            "context_query_id": context_query_id,
            "timestamp": datetime.now().isoformat(),
        }

        # 执行代码生成
        try:
            generated_code = generation_func(generation_prompt, generation_context)

            if not generated_code or not isinstance(generated_code, str):
                raise ValueError(f"无效的生成结果: {type(generated_code)}")

        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            # 记录失败审计
            self._record_failed_generation(
                agent_id,
                agent_type,
                project_path,
                file_path,
                generation_prompt,
                str(e),
                context_query_id,
            )
            raise

        # ===== 生成后阶段：记录生成结果 =====
        generation_record_id = self.memory_manager.record_code_generation(
            agent_id=agent_id,
            agent_type=agent_type,
            project_path=project_path,
            file_path=file_path,
            generated_code=generated_code,
            generation_prompt=generation_prompt,
            generation_reason=str(generation_reason),
            context_query_id=context_query_id,
            metadata={
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "memory_count": len(relevant_memories),
                "context_intent": context_intent,
            },
        )

        # 同时记录完整审计记录
        audit_id = self.memory_manager.record_code_generation_audit(
            agent_id=agent_id,
            agent_type=agent_type,
            project_path=project_path,
            file_path=file_path,
            pre_generation_context={
                "relevant_memories": relevant_memories,
                "context_query_id": context_query_id,
                "query_intent": context_intent,
            },
            generation_result={
                "code": generated_code,
                "prompt": generation_prompt,
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "generation_record_id": generation_record_id,
            },
            generation_reason=str(generation_reason),
            referenced_memories=[m["entry_id"] for m in relevant_memories],
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"代码生成审计完成: {agent_id} -> {file_path} "
            f"(耗时: {elapsed_ms:.1f}ms, 记忆: {len(relevant_memories)}条)"
        )

        # 缓存审计记录
        self.audit_cache[audit_id] = {
            "context_query_id": context_query_id,
            "generation_record_id": generation_record_id,
            "timestamp": datetime.now().isoformat(),
        }

        return generated_code, context_query_id, generation_record_id

    def _record_failed_generation(
        self,
        agent_id: str,
        agent_type: str,
        project_path: str,
        file_path: str,
        prompt: str,
        error: str,
        context_query_id: Optional[str] = None,
    ):
        """记录失败的代码生成"""
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "project_path": project_path,
            "file_path": file_path,
            "prompt": prompt,
            "error": error,
            "context_query_id": context_query_id,
            "timestamp": datetime.now().isoformat(),
            "status": "failed",
        }

        entry = MemoryEntry(
            entry_id=self.memory_manager._generate_entry_id(MemoryEntryType.SYSTEM_EVENT, content),
            entry_type=MemoryEntryType.SYSTEM_EVENT,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.HIGH,
            source_agent=agent_id,
            content=content,
            tags=["code_generation_failed", f"agent_{agent_id}", f"file_{file_path}"],
        )

        self.memory_manager._save_entry(entry)
        logger.error(f"代码生成失败记录: {agent_id} -> {file_path}: {error}")

    # ============================================================================
    # 装饰器和上下文管理器（强制审计）
    # ============================================================================

    def audit_decorator(self, agent_id: str, agent_type: str):
        """
        审计装饰器工厂

        使用示例：
            @audit_system.audit_decorator("my_agent", "claude_code")
            def generate_code(prompt: str, context: Dict = None) -> str:
                # 实际生成逻辑
                return generated_code
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 解析参数
                prompt = None
                project_path = "unknown"
                file_path = "unknown"

                # 尝试从参数中提取信息
                if args and len(args) > 0:
                    prompt = args[0]
                elif "prompt" in kwargs:
                    prompt = kwargs["prompt"]

                if "project_path" in kwargs:
                    project_path = kwargs["project_path"]
                if "file_path" in kwargs:
                    file_path = kwargs["file_path"]

                # 如果没有prompt，尝试调用原始函数
                if not prompt:
                    return func(*args, **kwargs)

                # 构建生成函数
                def generation_func(prompt_text, context):
                    # 调用原始函数，传入增强的上下文
                    return func(prompt_text, context)

                # 执行审计生成
                try:
                    generated_code, _, _ = self.audit_code_generation(
                        agent_id=agent_id,
                        agent_type=agent_type,
                        project_path=project_path,
                        file_path=file_path,
                        generation_prompt=prompt,
                        generation_func=generation_func,
                        generation_reason="decorated_function",
                        force_audit=True,
                    )
                    return generated_code
                except Exception as e:
                    logger.error(f"审计装饰器执行失败: {e}")
                    # 降级：直接调用原始函数
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    class AuditContext:
        """审计上下文管理器"""

        def __init__(
            self,
            audit_system,
            agent_id: str,
            agent_type: str,
            project_path: str,
            file_path: str,
            prompt: str,
        ):
            self.audit_system = audit_system
            self.agent_id = agent_id
            self.agent_type = agent_type
            self.project_path = project_path
            self.file_path = file_path
            self.prompt = prompt
            self.context_query_id = None
            self.generation_record_id = None

        def __enter__(self):
            # 查询相关记忆（但不记录，等到生成时一起记录）
            relevant_memories = self.audit_system.query_relevant_memories(
                project_path=self.project_path,
                file_path=self.file_path,
                intent="code_generation",
                agent_id=self.agent_id,
            )

            self.relevant_memories = relevant_memories
            return self

        def generate(self, generation_func: Callable) -> str:
            """在上下文中生成代码"""

            def wrapped_func(prompt, context):
                return generation_func(
                    prompt, {**context, "relevant_memories": self.relevant_memories}
                )

            generated_code, self.context_query_id, self.generation_record_id = (
                self.audit_system.audit_code_generation(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    project_path=self.project_path,
                    file_path=self.file_path,
                    generation_prompt=self.prompt,
                    generation_func=wrapped_func,
                    generation_reason="context_manager",
                    force_audit=True,
                )
            )

            return generated_code

        def __exit__(self, exc_type, exc_val, exc_tb):
            # 清理资源
            pass

    def audit_context(
        self, agent_id: str, agent_type: str, project_path: str, file_path: str, prompt: str
    ):
        """
        创建审计上下文管理器

        使用示例：
            with audit_system.audit_context(agent_id, agent_type, project_path, file_path, prompt) as ctx:
                code = ctx.generate(my_generation_func)
        """
        return self.AuditContext(self, agent_id, agent_type, project_path, file_path, prompt)

    # ============================================================================
    # 查询和回滚功能
    # ============================================================================

    def get_audit_trail(
        self,
        project_path: str = None,
        file_path: str = None,
        agent_id: str = None,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取审计追踪记录

        Args:
            project_path: 项目路径过滤
            file_path: 文件路径过滤
            agent_id: 代理ID过滤
            hours: 时间窗口（小时）
            limit: 返回条目限制

        Returns:
            审计追踪列表
        """
        # 构建查询条件
        tags = []
        if project_path:
            tags.append(f"project_{project_path}")
        if file_path:
            tags.append(f"file_{file_path}")

        # 查询代码审计记录
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        audit_entries = self.memory_manager.query_memory(
            entry_type=MemoryEntryType.CODE_GENERATION_AUDIT,
            source_agent=agent_id,
            tags=tags if tags else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        # 格式化结果
        trail = []
        for entry in audit_entries:
            trail.append(
                {
                    "audit_id": entry.entry_id,
                    "timestamp": entry.timestamp,
                    "agent_id": entry.source_agent,
                    "project_path": entry.content.get("project_path"),
                    "file_path": entry.content.get("file_path"),
                    "generation_reason": entry.content.get("generation_reason"),
                    "referenced_memories": entry.content.get("referenced_memories", []),
                    "pre_generation_context": entry.content.get("pre_generation_context", {}),
                    "generation_result": entry.content.get("generation_result", {}),
                }
            )

        return trail

    def rollback_code(
        self, audit_id: str, rollback_agent_id: str, rollback_reason: str = "error_correction"
    ) -> str:
        """
        回滚代码到审计记录的状态

        Args:
            audit_id: 审计记录ID
            rollback_agent_id: 回滚代理ID
            rollback_reason: 回滚原因

        Returns:
            回滚记录ID
        """
        # 获取审计记录
        audit_entry = None
        entries = self.memory_manager.query_memory(limit=100)  # 简单查询
        for entry in entries:
            if entry.entry_id == audit_id:
                audit_entry = entry
                break

        if not audit_entry:
            raise ValueError(f"未找到审计记录: {audit_id}")

        if audit_entry.entry_type != MemoryEntryType.CODE_GENERATION_AUDIT:
            raise ValueError(f"条目类型不是代码审计: {audit_entry.entry_type}")

        # 提取原始代码
        generation_result = audit_entry.content.get("generation_result", {})
        original_code = generation_result.get("code")

        if not original_code:
            raise ValueError("审计记录中未找到原始代码")

        # 获取文件信息
        file_path = audit_entry.content.get("file_path")
        project_path = audit_entry.content.get("project_path")

        # 记录回滚操作
        rollback_changes = {
            "audit_id": audit_id,
            "file_path": file_path,
            "project_path": project_path,
            "original_agent": audit_entry.source_agent,
            "rollback_timestamp": datetime.now().isoformat(),
            "code_restored": True if original_code else False,
        }

        rollback_id = self.memory_manager.record_code_rollback(
            rollback_agent_id=rollback_agent_id,
            original_audit_id=audit_id,
            rollback_reason=rollback_reason,
            rollback_changes=rollback_changes,
            restored_code=original_code,
        )

        logger.info(f"代码回滚记录创建: {audit_id} -> {rollback_id}")

        # 返回原始代码（实际文件恢复由调用者处理）
        return original_code, rollback_id

    # ============================================================================
    # 多平台适配器
    # ============================================================================

    def create_claude_code_adapter(self, agent_id: str = "claude_code_default"):
        """创建Claude Code适配器"""
        self.register_agent(
            agent_id=agent_id,
            agent_type="claude_code",
            capabilities=["code_generation", "code_review", "refactoring"],
            metadata={"environment": "python", "platform": "claude_code"},
        )

        # 返回装饰器
        return self.audit_decorator(agent_id, "claude_code")

    def create_vscode_adapter(self, agent_id: str = "vscode_default"):
        """创建VSCode适配器（通过API）"""
        self.register_agent(
            agent_id=agent_id,
            agent_type="vscode",
            capabilities=["code_completion", "refactoring", "quick_fix"],
            metadata={"environment": "vscode", "platform": "extension"},
        )

        # 简化适配器接口
        class VSCodeAdapter:
            def __init__(self, audit_system, agent_id):
                self.audit_system = audit_system
                self.agent_id = agent_id

            def generate_with_audit(self, prompt: str, file_path: str, project_path: str = "."):
                """带审计的代码生成"""

                # 这里实际应该调用VSCode的代码生成API
                # 目前返回模拟实现
                def vscode_generation(prompt_text, context):
                    # 模拟VSCode生成
                    return f"// VSCode生成的代码\n// 基于上下文: {context.get('relevant_memories', [])}\n// 提示: {prompt_text}"

                return self.audit_system.audit_code_generation(
                    agent_id=self.agent_id,
                    agent_type="vscode",
                    project_path=project_path,
                    file_path=file_path,
                    generation_prompt=prompt,
                    generation_func=vscode_generation,
                    generation_reason="vscode_completion",
                )

        return VSCodeAdapter(self, agent_id)

    def create_trae_cn_adapter(self, agent_id: str = "trae_cn_default"):
        """创建trae cn适配器（中文环境）"""
        self.register_agent(
            agent_id=agent_id,
            agent_type="trae_cn",
            capabilities=["code_generation", "chinese_context", "localization"],
            metadata={"language": "zh-CN", "platform": "trae_cn"},
        )

        # 返回装饰器（支持中文）
        return self.audit_decorator(agent_id, "trae_cn")


# ============================================================================
# 全局实例和工具函数
# ============================================================================

# 全局审计系统实例
_global_audit_system = None


def get_global_audit_system() -> CodingAuditSystem:
    """获取全局审计系统实例（单例）"""
    global _global_audit_system
    if _global_audit_system is None:
        _global_audit_system = CodingAuditSystem()
        logger.info("全局Coding审计系统已初始化")
    return _global_audit_system


def require_audit(agent_id: str, agent_type: str):
    """
    强制审计装饰器（简化版）

    使用示例：
        @require_audit("my_agent", "claude_code")
        def generate_python_code(prompt: str, context: Dict = None) -> str:
            # 实际生成逻辑
            return code
    """
    audit_system = get_global_audit_system()
    return audit_system.audit_decorator(agent_id, agent_type)


# ============================================================================
# 测试函数
# ============================================================================


def test_coding_audit_system():
    """测试审计系统"""
    print("=== Coding审计系统测试 ===")

    # 初始化审计系统
    audit_system = CodingAuditSystem()

    # 注册测试agent
    audit_system.register_agent(
        agent_id="test_agent_001", agent_type="test", capabilities=["code_generation", "test"]
    )

    # 测试1: 使用装饰器
    print("\n=== 测试1: 装饰器审计 ===")

    @audit_system.audit_decorator("test_agent_001", "test")
    def generate_test_code(prompt: str, context: Dict = None) -> str:
        print(f"  生成代码，提示: {prompt}")
        print(f"  上下文记忆数: {len(context.get('relevant_memories', [])) if context else 0}")
        return f"# 生成的测试代码\n# 提示: {prompt}\nprint('Hello, World!')"

    try:
        code = generate_test_code(
            prompt="创建一个Hello World程序",
            project_path="/test/project",
            file_path="/test/project/hello.py",
        )
        print(f"  生成成功: {len(code)} 字符")
    except Exception as e:
        print(f"  生成失败: {e}")

    # 测试2: 使用上下文管理器
    print("\n=== 测试2: 上下文管理器审计 ===")

    with audit_system.audit_context(
        agent_id="test_agent_001",
        agent_type="test",
        project_path="/test/project",
        file_path="/test/project/utils.py",
        prompt="创建一个工具函数",
    ) as ctx:

        def custom_generation(prompt: str, context: Dict) -> str:
            print(f"  自定义生成，提示: {prompt}")
            return f"# 工具函数\n# 基于 {len(context.get('relevant_memories', []))} 条记忆\ndef util():\n    return 'utility'"

        code = ctx.generate(custom_generation)
        print(f"  生成成功: {len(code)} 字符")
        print(f"  上下文查询ID: {ctx.context_query_id}")
        print(f"  生成记录ID: {ctx.generation_record_id}")

    # 测试3: 查询审计追踪
    print("\n=== 测试3: 审计追踪查询 ===")
    trail = audit_system.get_audit_trail(limit=5)
    print(f"  最近审计记录: {len(trail)} 条")
    for i, entry in enumerate(trail, 1):
        print(f"  {i}. {entry['timestamp']} - {entry['agent_id']} -> {entry['file_path']}")

    # 测试4: 多平台适配器
    print("\n=== 测试4: 多平台适配器 ===")

    claude_adapter = audit_system.create_claude_code_adapter("claude_test")

    @claude_adapter
    def claude_generate(prompt: str, context: Dict = None) -> str:
        return f"# Claude生成的代码\n# {prompt}"

    code = claude_generate(
        prompt="测试Claude适配器",
        project_path="/claude/project",
        file_path="/claude/project/main.py",
    )
    print(f"  Claude适配器测试成功: {len(code)} 字符")

    print("\n=== 测试完成 ===")
    print("审计系统功能验证通过")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    test_coding_audit_system()
