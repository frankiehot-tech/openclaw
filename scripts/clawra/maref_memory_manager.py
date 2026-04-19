#!/usr/bin/env python3
"""
MAREF内存管理器
支持系统变动记录和全域认知对齐

核心功能：
1. 系统状态变更记录 - 每次卦象状态转换都记录到内存
2. 智能体活动跟踪 - 记录每个智能体的决策和行动
3. 全局认知对齐 - 提供统一的内存查询API，确保所有智能体对系统状态有一致认知
4. 记忆存储和检索 - 结构化存储，支持按时间、智能体、卦象类型等维度查询
5. 与现有监控系统集成 - 与MAREF监控和日报系统共享数据
"""

import hashlib
import json
import logging
import queue
import sqlite3
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml


class MemoryEntryType(str, Enum):
    """内存条目类型枚举"""

    STATE_TRANSITION = "state_transition"  # 卦象状态转换
    AGENT_ACTION = "agent_action"  # 智能体行动
    AGENT_DECISION = "agent_decision"  # 智能体决策
    SYSTEM_EVENT = "system_event"  # 系统事件
    PERFORMANCE_METRIC = "performance_metric"  # 性能指标
    ALERT_NOTIFICATION = "alert_notification"  # 预警通知
    COGNITIVE_ALIGNMENT = "cognitive_alignment"  # 认知对齐事件
    # 代码审计相关类型
    CODE_GENERATION_AUDIT = "code_generation_audit"  # 代码生成完整审计记录
    CODE_CONTEXT_QUERY = "code_context_query"  # 生成前上下文查询
    CODE_GENERATION = "code_generation"  # 代码生成结果
    CODE_ROLLBACK = "code_rollback"  # 代码回滚操作
    AGENT_INTERACTION = "agent_interaction"  # Agent间交互历史


class MemoryPriority(str, Enum):
    """内存条目优先级"""

    LOW = "low"  # 低优先级，常规记录
    MEDIUM = "medium"  # 中等优先级，重要事件
    HIGH = "high"  # 高优先级，关键决策
    CRITICAL = "critical"  # 关键优先级，系统状态转换


@dataclass
class MemoryEntry:
    """内存条目数据结构"""

    entry_id: str
    entry_type: MemoryEntryType
    timestamp: str
    priority: MemoryPriority
    source_agent: str
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # 相关条目引用
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "source_agent": self.source_agent,
            "content": self.content,
            "tags": self.tags,
            "references": self.references,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """从字典创建"""
        return cls(
            entry_id=data["entry_id"],
            entry_type=MemoryEntryType(data["entry_type"]),
            timestamp=data["timestamp"],
            priority=MemoryPriority(data["priority"]),
            source_agent=data["source_agent"],
            content=data["content"],
            tags=data.get("tags", []),
            references=data.get("references", []),
            metadata=data.get("metadata", {}),
        )


class MAREFMemoryManager:
    """
    MAREF内存管理器

    职责：
    1. 记录系统状态转换（卦象转换）
    2. 跟踪智能体活动和决策
    3. 提供统一的内存查询接口
    4. 确保全域认知对齐
    5. 管理内存存储和检索
    """

    def __init__(self, memory_dir: str = None, db_path: str = None, performance_mode: bool = False):
        """
        初始化内存管理器

        Args:
            memory_dir: 内存文件存储目录（JSON格式）
            db_path: SQLite数据库路径（可选）
            performance_mode: 性能模式（为速度优化，可能降低数据完整性）
        """
        # 设置内存目录
        if memory_dir:
            self.memory_dir = Path(memory_dir)
        else:
            self.memory_dir = Path("/Volumes/1TB-M2/openclaw/memory/maref")

        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # SQLite数据库路径
        self.db_path = db_path or str(self.memory_dir / "maref_memory.db")

        # 性能模式设置
        self.performance_mode = performance_mode

        # 异步写入队列（用于性能优化）
        self.write_queue = queue.Queue(maxsize=10000)
        self.writer_thread = None
        self.writer_running = False

        # 同步写入计数器（用于性能测试）
        self.sync_write_count = 0
        self.async_write_count = 0

        # 初始化日志
        self.logger = self._setup_logger()

        # 初始化数据库
        self._init_database()

        # 缓存最近的内存条目
        self.recent_entries: List[MemoryEntry] = []
        self.max_cached_entries = 1000

        # 启动异步写入线程（如果不处于性能模式）
        if not self.performance_mode:
            self._start_async_writer()

        self.logger.info(f"MAREF内存管理器初始化完成，存储目录: {self.memory_dir}")
        self.logger.info(f"数据库路径: {self.db_path}")
        self.logger.info(f"性能模式: {'开启' if performance_mode else '关闭'}")

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"maref_memory_manager")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _start_async_writer(self):
        """启动异步写入线程"""
        if self.writer_thread is None or not self.writer_thread.is_alive():
            self.writer_running = True
            self.writer_thread = threading.Thread(
                target=self._async_writer_worker, name="MAREFMemoryWriter", daemon=True
            )
            self.writer_thread.start()
            self.logger.info("异步写入线程已启动")

    def _stop_async_writer(self):
        """停止异步写入线程"""
        self.writer_running = False
        if self.writer_thread:
            # 向队列发送停止信号
            self.write_queue.put(None)
            self.writer_thread.join(timeout=5.0)
            if self.writer_thread.is_alive():
                self.logger.warning("异步写入线程未能及时停止")
            else:
                self.logger.info("异步写入线程已停止")
            self.writer_thread = None

    def _async_writer_worker(self):
        """异步写入工作线程"""
        batch_size = 10  # 批量写入大小
        max_wait_time = 1.0  # 最大等待时间（秒）
        batch = []

        while self.writer_running:
            try:
                # 等待条目，最多等待max_wait_time
                try:
                    entry = self.write_queue.get(timeout=max_wait_time)
                except queue.Empty:
                    entry = None

                # 如果是停止信号，跳出循环
                if entry is None:
                    break

                # 添加到批量
                batch.append(entry)

                # 如果达到批量大小，或者队列为空，执行批量写入
                if len(batch) >= batch_size or self.write_queue.empty():
                    if batch:
                        try:
                            self._batch_save_to_database(batch)
                            self.async_write_count += len(batch)
                            batch.clear()
                        except Exception as e:
                            self.logger.error(f"批量写入失败: {e}")
                            # 失败后重新尝试单个写入
                            for failed_entry in batch:
                                try:
                                    self._save_to_database(failed_entry)
                                    self.async_write_count += 1
                                except Exception as e2:
                                    self.logger.error(f"单个条目写入也失败: {e2}")
                            batch.clear()

                # 标记任务完成
                self.write_queue.task_done()

            except Exception as e:
                self.logger.error(f"异步写入工作线程异常: {e}")
                import traceback

                self.logger.error(traceback.format_exc())

        # 退出前处理剩余批量
        if batch:
            try:
                self._batch_save_to_database(batch)
                self.async_write_count += len(batch)
            except Exception as e:
                self.logger.error(f"最终批量写入失败: {e}")

    def _batch_save_to_database(self, entries: List[MemoryEntry]):
        """批量保存到数据库（性能优化）"""
        if not entries:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 使用事务
            cursor.execute("BEGIN TRANSACTION")

            for entry in entries:
                # 插入主条目
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO memory_entries
                    (entry_id, entry_type, timestamp, priority, source_agent,
                     content_json, tags_json, references_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        entry.entry_id,
                        entry.entry_type.value,
                        entry.timestamp,
                        entry.priority.value,
                        entry.source_agent,
                        json.dumps(entry.content, ensure_ascii=False),
                        json.dumps(entry.tags, ensure_ascii=False),
                        json.dumps(entry.references, ensure_ascii=False),
                        json.dumps(entry.metadata, ensure_ascii=False),
                    ),
                )

                # 插入标签
                for tag in entry.tags:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO memory_tags (entry_id, tag)
                        VALUES (?, ?)
                    """,
                        (entry.entry_id, tag),
                    )

                # 插入引用
                for ref_entry_id in entry.references:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO memory_references (entry_id, referenced_entry_id)
                        VALUES (?, ?)
                    """,
                        (entry.entry_id, ref_entry_id),
                    )

            conn.commit()
            self.logger.debug(f"批量写入完成，保存了 {len(entries)} 个条目")

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建内存条目表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    entry_id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    source_agent TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_entry_type ON memory_entries(entry_type)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_agent ON memory_entries(source_agent)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON memory_entries(priority)")

            # 创建标签索引表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_tags (
                    entry_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES memory_entries (entry_id) ON DELETE CASCADE,
                    PRIMARY KEY (entry_id, tag)
                )
            """)

            # 创建引用关系表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_references (
                    entry_id TEXT NOT NULL,
                    referenced_entry_id TEXT NOT NULL,
                    reference_type TEXT DEFAULT 'general',
                    FOREIGN KEY (entry_id) REFERENCES memory_entries (entry_id) ON DELETE CASCADE,
                    PRIMARY KEY (entry_id, referenced_entry_id)
                )
            """)

            conn.commit()
            conn.close()

            self.logger.info("内存数据库初始化完成")

        except Exception as e:
            self.logger.error(f"初始化数据库失败: {e}")
            # 回退到文件存储
            self.db_path = None

    def _generate_entry_id(self, entry_type: MemoryEntryType, content: Dict[str, Any]) -> str:
        """生成内存条目ID"""
        timestamp = datetime.now().isoformat()
        content_str = json.dumps(content, sort_keys=True)
        hash_input = f"{entry_type.value}:{timestamp}:{content_str}"

        # 使用SHA-256生成短哈希
        hash_obj = hashlib.sha256(hash_input.encode("utf-8"))
        return f"mem_{entry_type.value[:3]}_{hash_obj.hexdigest()[:16]}"

    def record_state_transition(
        self,
        from_state: str,
        to_state: str,
        trigger_agent: str,
        context: Dict[str, Any] = None,
        transition_reason: str = "",
    ) -> str:
        """
        记录卦象状态转换

        Args:
            from_state: 源卦象状态（二进制表示）
            to_state: 目标卦象状态（二进制表示）
            trigger_agent: 触发转换的智能体
            context: 转换上下文信息
            transition_reason: 转换原因描述

        Returns:
            内存条目ID
        """
        # 确保转换原因不为空
        final_reason = transition_reason if transition_reason else "状态转换"

        content = {
            "from_state": from_state,
            "to_state": to_state,
            "transition_reason": final_reason,
            "context": context or {},
            "hamming_distance": self._calculate_hamming_distance(from_state, to_state),
            "is_gray_code_compliant": self._is_gray_code_compliant(from_state, to_state),
        }

        tags = [
            "state_transition",
            f"from_{from_state}",
            f"to_{to_state}",
            f"agent_{trigger_agent}",
            "hexagram_change",
        ]

        # 如果不符合格雷编码，添加警告标签
        if not content["is_gray_code_compliant"]:
            tags.append("gray_code_violation")

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.STATE_TRANSITION, content),
            entry_type=MemoryEntryType.STATE_TRANSITION,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.HIGH,
            source_agent=trigger_agent,
            content=content,
            tags=tags,
        )

        return self._save_entry(entry)

    def record_agent_action(
        self,
        agent_id: str,
        agent_type: str,
        action_type: str,
        action_details: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录智能体行动

        Args:
            agent_id: 智能体ID
            agent_type: 智能体类型
            action_type: 行动类型
            action_details: 行动详细信息
            result: 行动结果（可选）
            decision_context: 决策上下文（可选）

        Returns:
            内存条目ID
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "action_type": action_type,
            "action_details": action_details,
            "result": result or {},
            "decision_context": decision_context or {},
            "timestamp": datetime.now().isoformat(),
        }

        tags = ["agent_action", f"agent_{agent_type}", f"action_{action_type}", agent_id]

        priority = MemoryPriority.MEDIUM
        if action_type in ["critical_decision", "system_change", "state_transition"]:
            priority = MemoryPriority.HIGH

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.AGENT_ACTION, content),
            entry_type=MemoryEntryType.AGENT_ACTION,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            source_agent=agent_id,
            content=content,
            tags=tags,
        )

        return self._save_entry(entry)

    def record_agent_decision(
        self,
        agent_id: str,
        agent_type: str,
        decision_type: str,
        decision_data: Dict[str, Any],
        alternatives: List[Dict[str, Any]] = None,
        rationale: str = "",
    ) -> str:
        """
        记录智能体决策

        Args:
            agent_id: 智能体ID
            agent_type: 智能体类型
            decision_type: 决策类型
            decision_data: 决策数据
            alternatives: 考虑的替代方案
            rationale: 决策理由

        Returns:
            内存条目ID
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "decision_type": decision_type,
            "decision_data": decision_data,
            "alternatives": alternatives or [],
            "rationale": rationale,
            "timestamp": datetime.now().isoformat(),
        }

        tags = ["agent_decision", f"agent_{agent_type}", f"decision_{decision_type}", agent_id]

        priority = MemoryPriority.MEDIUM
        if decision_type in ["critical_choice", "system_design", "architecture_change"]:
            priority = MemoryPriority.HIGH

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.AGENT_DECISION, content),
            entry_type=MemoryEntryType.AGENT_DECISION,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            source_agent=agent_id,
            content=content,
            tags=tags,
        )

        return self._save_entry(entry)

    def record_system_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "info",
        source: str = "system",
    ) -> str:
        """
        记录系统事件

        Args:
            event_type: 事件类型
            event_data: 事件数据
            severity: 严重程度 (info, warning, error, critical)
            source: 事件来源

        Returns:
            内存条目ID
        """
        content = {
            "event_type": event_type,
            "event_data": event_data,
            "severity": severity,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }

        tags = ["system_event", f"event_{event_type}", f"severity_{severity}", source]

        # 根据严重程度设置优先级
        priority_map = {
            "info": MemoryPriority.LOW,
            "warning": MemoryPriority.MEDIUM,
            "error": MemoryPriority.HIGH,
            "critical": MemoryPriority.CRITICAL,
        }
        priority = priority_map.get(severity, MemoryPriority.MEDIUM)

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.SYSTEM_EVENT, content),
            entry_type=MemoryEntryType.SYSTEM_EVENT,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            source_agent=source,
            content=content,
            tags=tags,
        )

        return self._save_entry(entry)

    def record_cognitive_alignment(
        self,
        alignment_type: str,
        involved_agents: List[str],
        alignment_data: Dict[str, Any],
        alignment_result: Dict[str, Any],
    ) -> str:
        """
        记录认知对齐事件

        Args:
            alignment_type: 对齐类型 (state, knowledge, decision, etc.)
            involved_agents: 涉及智能体列表
            alignment_data: 对齐数据
            alignment_result: 对齐结果

        Returns:
            内存条目ID
        """
        content = {
            "alignment_type": alignment_type,
            "involved_agents": involved_agents,
            "alignment_data": alignment_data,
            "alignment_result": alignment_result,
            "timestamp": datetime.now().isoformat(),
        }

        tags = [
            "cognitive_alignment",
            f"alignment_{alignment_type}",
            f"agents_{len(involved_agents)}",
        ]

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.COGNITIVE_ALIGNMENT, content),
            entry_type=MemoryEntryType.COGNITIVE_ALIGNMENT,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.HIGH,
            source_agent="memory_manager",
            content=content,
            tags=tags,
        )

        entry_id = self._save_entry(entry)

        # 为涉及的每个智能体创建引用
        for agent_id in involved_agents:
            self._add_reference(entry_id, f"agent_{agent_id}", "involvement")

        return entry_id

    def record_code_generation_audit(
        self,
        agent_id: str,
        agent_type: str,
        project_path: str,
        file_path: str,
        pre_generation_context: Dict[str, Any],
        generation_result: Dict[str, Any],
        generation_reason: str,
        referenced_memories: List[str] = None,
    ) -> str:
        """
        记录代码生成审计（完整记录生成前后的所有信息）

        Args:
            agent_id: 生成代理ID
            agent_type: 代理类型 (claude_code, vscode, open_code, codex, trae_cn, etc.)
            project_path: 项目路径
            file_path: 文件路径
            pre_generation_context: 生成前上下文（查询的记忆、意图、约束等）
            generation_result: 生成结果（代码、元数据、耗时等）
            generation_reason: 生成原因（用户请求、修复bug、重构等）
            referenced_memories: 引用的记忆条目ID列表

        Returns:
            审计记录ID
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "project_path": project_path,
            "file_path": file_path,
            "pre_generation_context": pre_generation_context,
            "generation_result": generation_result,
            "generation_reason": generation_reason,
            "timestamp": datetime.now().isoformat(),
            "audit_phase": "complete",  # complete, pre_only, post_only
        }

        tags = [
            "code_generation",
            "audit",
            f"agent_type_{agent_type}",
            f"project_{project_path}",
            f"file_{file_path}",
        ]

        if referenced_memories:
            content["referenced_memories"] = referenced_memories
            tags.append(f"references_{len(referenced_memories)}")

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.CODE_GENERATION_AUDIT, content),
            entry_type=MemoryEntryType.CODE_GENERATION_AUDIT,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.HIGH,
            source_agent=agent_id,
            content=content,
            tags=tags,
        )

        entry_id = self._save_entry(entry)
        self.logger.info(f"代码生成审计记录成功: {agent_id} -> {file_path}")
        return entry_id

    def record_code_rollback(
        self,
        rollback_agent_id: str,
        original_audit_id: str,
        rollback_reason: str,
        rollback_changes: Dict[str, Any],
        restored_code: Optional[str] = None,
    ) -> str:
        """
        记录代码回滚操作

        Args:
            rollback_agent_id: 回滚代理ID
            original_audit_id: 原始审计记录ID
            rollback_reason: 回滚原因
            rollback_changes: 回滚变更详情
            restored_code: 恢复的代码内容（可选）

        Returns:
            回滚记录ID
        """
        content = {
            "rollback_agent_id": rollback_agent_id,
            "original_audit_id": original_audit_id,
            "rollback_reason": rollback_reason,
            "rollback_changes": rollback_changes,
            "timestamp": datetime.now().isoformat(),
        }

        if restored_code:
            content["restored_code"] = restored_code

        tags = [
            "code_rollback",
            f"agent_{rollback_agent_id}",
            f"original_audit_{original_audit_id}",
        ]

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.CODE_ROLLBACK, content),
            entry_type=MemoryEntryType.CODE_ROLLBACK,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.CRITICAL,  # 回滚是关键操作
            source_agent=rollback_agent_id,
            content=content,
            tags=tags,
        )

        entry_id = self._save_entry(entry)
        self.logger.info(f"代码回滚记录成功: {original_audit_id} -> {entry_id}")
        return entry_id

    def record_code_context_query(
        self,
        agent_id: str,
        agent_type: str,
        project_path: str,
        file_path: str,
        query_intent: str,
        query_parameters: Dict[str, Any],
        query_results: List[Dict[str, Any]],
    ) -> str:
        """
        记录代码生成前的上下文查询

        Args:
            agent_id: 代理ID
            agent_type: 代理类型
            project_path: 项目路径
            file_path: 文件路径
            query_intent: 查询意图（需要什么信息）
            query_parameters: 查询参数
            query_results: 查询结果（相关记忆）

        Returns:
            查询记录ID
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "project_path": project_path,
            "file_path": file_path,
            "query_intent": query_intent,
            "query_parameters": query_parameters,
            "query_results": query_results,
            "timestamp": datetime.now().isoformat(),
            "audit_phase": "pre_generation",
        }

        tags = [
            "code_context_query",
            f"agent_type_{agent_type}",
            f"project_{project_path}",
            f"file_{file_path}",
            f"intent_{query_intent}",
        ]

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.CODE_CONTEXT_QUERY, content),
            entry_type=MemoryEntryType.CODE_CONTEXT_QUERY,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.MEDIUM,
            source_agent=agent_id,
            content=content,
            tags=tags,
        )

        entry_id = self._save_entry(entry)
        self.logger.debug(f"代码上下文查询记录: {agent_id} -> {query_intent}")
        return entry_id

    def record_code_generation(
        self,
        agent_id: str,
        agent_type: str,
        project_path: str,
        file_path: str,
        generated_code: str,
        generation_prompt: str,
        generation_reason: str,
        context_query_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录代码生成结果

        Args:
            agent_id: 代理ID
            agent_type: 代理类型
            project_path: 项目路径
            file_path: 文件路径
            generated_code: 生成的代码
            generation_prompt: 生成提示
            generation_reason: 生成原因
            context_query_id: 关联的上下文查询ID（可选）
            metadata: 额外元数据

        Returns:
            生成记录ID
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "project_path": project_path,
            "file_path": file_path,
            "generated_code": generated_code,
            "generation_prompt": generation_prompt,
            "generation_reason": generation_reason,
            "timestamp": datetime.now().isoformat(),
            "audit_phase": "post_generation",
        }

        if context_query_id:
            content["context_query_id"] = context_query_id
        if metadata:
            content["metadata"] = metadata

        tags = [
            "code_generation",
            f"agent_type_{agent_type}",
            f"project_{project_path}",
            f"file_{file_path}",
        ]

        entry = MemoryEntry(
            entry_id=self._generate_entry_id(MemoryEntryType.CODE_GENERATION, content),
            entry_type=MemoryEntryType.CODE_GENERATION,
            timestamp=datetime.now().isoformat(),
            priority=MemoryPriority.HIGH,
            source_agent=agent_id,
            content=content,
            tags=tags,
        )

        entry_id = self._save_entry(entry)
        self.logger.info(f"代码生成记录: {agent_id} -> {file_path}")
        return entry_id

    def _calculate_hamming_distance(self, state1: str, state2: str) -> int:
        """计算汉明距离"""
        if len(state1) != len(state2):
            return len(state1)  # 长度不同，返回最大距离

        distance = 0
        for c1, c2 in zip(state1, state2):
            if c1 != c2:
                distance += 1
        return distance

    def _is_gray_code_compliant(self, state1: str, state2: str) -> bool:
        """检查是否符合格雷编码（汉明距离=1）"""
        return self._calculate_hamming_distance(state1, state2) == 1

    def _save_entry(self, entry: MemoryEntry) -> str:
        """
        保存内存条目

        Args:
            entry: 内存条目

        Returns:
            条目ID
        """
        try:
            # 性能模式：仅更新缓存，不保存到数据库
            if self.performance_mode:
                self._update_cache(entry)
                self.logger.debug(
                    f"性能模式：内存条目仅缓存: {entry.entry_id} [{entry.entry_type.value}]"
                )
                return entry.entry_id

            # 异步写入：添加到队列
            if not self.performance_mode and self.writer_running:
                try:
                    self.write_queue.put(entry, block=True, timeout=0.1)
                    self.logger.debug(
                        f"内存条目已加入异步队列: {entry.entry_id} [{entry.entry_type.value}]"
                    )

                    # 仍然更新缓存（立即可用）
                    self._update_cache(entry)

                    # 异步保存到JSON文件（不阻塞）
                    threading.Thread(
                        target=self._save_to_json_file, args=(entry,), daemon=True
                    ).start()

                    return entry.entry_id

                except queue.Full:
                    self.logger.warning("写入队列已满，回退到同步写入")
                    # 队列满，回退到同步写入

            # 同步写入（回退或性能模式关闭）
            self.sync_write_count += 1

            # 保存到数据库
            if self.db_path:
                self._save_to_database(entry)

            # 同时保存到JSON文件（备份）
            self._save_to_json_file(entry)

            # 更新缓存
            self._update_cache(entry)

            self.logger.debug(f"内存条目已同步保存: {entry.entry_id} [{entry.entry_type.value}]")
            return entry.entry_id

        except Exception as e:
            self.logger.error(f"保存内存条目失败: {e}")
            raise

    def _save_to_database(self, entry: MemoryEntry):
        """保存到SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 插入主条目
            cursor.execute(
                """
                INSERT OR REPLACE INTO memory_entries
                (entry_id, entry_type, timestamp, priority, source_agent,
                 content_json, tags_json, references_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.entry_id,
                    entry.entry_type.value,
                    entry.timestamp,
                    entry.priority.value,
                    entry.source_agent,
                    json.dumps(entry.content, ensure_ascii=False),
                    json.dumps(entry.tags, ensure_ascii=False),
                    json.dumps(entry.references, ensure_ascii=False),
                    json.dumps(entry.metadata, ensure_ascii=False),
                ),
            )

            # 插入标签
            for tag in entry.tags:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO memory_tags (entry_id, tag)
                    VALUES (?, ?)
                """,
                    (entry.entry_id, tag),
                )

            # 插入引用
            for ref_entry_id in entry.references:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO memory_references (entry_id, referenced_entry_id)
                    VALUES (?, ?)
                """,
                    (entry.entry_id, ref_entry_id),
                )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _save_to_json_file(self, entry: MemoryEntry):
        """保存到JSON文件（按日期组织）"""
        try:
            # 按日期组织文件
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_dir = self.memory_dir / date_str[:7]  # 按年月组织
            file_dir.mkdir(parents=True, exist_ok=True)

            file_path = file_dir / f"memory_{date_str}.jsonl"

            # 使用JSONL格式，每行一个条目
            entry_dict = entry.to_dict()
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")

        except Exception as e:
            self.logger.warning(f"保存到JSON文件失败，使用回退存储: {e}")
            # 回退到简单文件存储
            self._fallback_save(entry)

    def _fallback_save(self, entry: MemoryEntry):
        """回退存储（当主要存储失败时）"""
        try:
            fallback_dir = self.memory_dir / "fallback"
            fallback_dir.mkdir(parents=True, exist_ok=True)

            file_path = fallback_dir / f"memory_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"

            entry_dict = entry.to_dict()
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")

        except Exception as e:
            self.logger.error(f"回退存储也失败: {e}")

    def _update_cache(self, entry: MemoryEntry):
        """更新内存缓存"""
        self.recent_entries.append(entry)

        # 限制缓存大小
        if len(self.recent_entries) > self.max_cached_entries:
            self.recent_entries = self.recent_entries[-self.max_cached_entries :]

    def _add_reference(self, entry_id: str, reference_key: str, reference_type: str = "general"):
        """添加引用关系"""
        # 在数据库中记录引用关系
        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO memory_references
                    (entry_id, referenced_entry_id, reference_type)
                    VALUES (?, ?, ?)
                """,
                    (entry_id, reference_key, reference_type),
                )

                conn.commit()
                conn.close()

            except Exception as e:
                self.logger.warning(f"添加引用失败: {e}")

    def query_memory(
        self,
        entry_type: Optional[MemoryEntryType] = None,
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryEntry]:
        """
        查询内存条目

        Args:
            entry_type: 条目类型过滤
            source_agent: 来源智能体过滤
            tags: 标签过滤
            start_time: 开始时间 (ISO格式)
            end_time: 结束时间 (ISO格式)
            priority: 优先级过滤
            limit: 返回条目数量限制
            offset: 偏移量

        Returns:
            内存条目列表
        """
        if self.db_path:
            return self._query_from_database(
                entry_type, source_agent, tags, start_time, end_time, priority, limit, offset
            )
        else:
            return self._query_from_cache(
                entry_type, source_agent, tags, start_time, end_time, priority, limit, offset
            )

    def _query_from_database(
        self,
        entry_type: Optional[MemoryEntryType] = None,
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryEntry]:
        """从数据库查询"""
        entries = []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if entry_type:
                conditions.append("entry_type = ?")
                params.append(entry_type.value)

            if source_agent:
                conditions.append("source_agent = ?")
                params.append(source_agent)

            if priority:
                conditions.append("priority = ?")
                params.append(priority.value)

            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)

            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)

            # 如果有标签条件，需要使用子查询
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(
                        "EXISTS (SELECT 1 FROM memory_tags mt WHERE mt.entry_id = me.entry_id AND mt.tag = ?)"
                    )
                    params.append(tag)
                conditions.append("(" + " AND ".join(tag_conditions) + ")")

            # 构建SQL
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT * FROM memory_entries me
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                entry_dict = {
                    "entry_id": row["entry_id"],
                    "entry_type": MemoryEntryType(row["entry_type"]),
                    "timestamp": row["timestamp"],
                    "priority": MemoryPriority(row["priority"]),
                    "source_agent": row["source_agent"],
                    "content": json.loads(row["content_json"]),
                    "tags": json.loads(row["tags_json"]),
                    "references": json.loads(row["references_json"]),
                    "metadata": json.loads(row["metadata_json"]),
                }
                entries.append(MemoryEntry.from_dict(entry_dict))

            conn.close()

        except Exception as e:
            self.logger.error(f"数据库查询失败: {e}")

        return entries

    def _query_from_cache(
        self,
        entry_type: Optional[MemoryEntryType] = None,
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryEntry]:
        """从缓存查询（数据库不可用时）"""
        filtered_entries = []

        for entry in self.recent_entries:
            # 应用过滤条件
            if entry_type and entry.entry_type != entry_type:
                continue

            if source_agent and entry.source_agent != source_agent:
                continue

            if priority and entry.priority != priority:
                continue

            if start_time and entry.timestamp < start_time:
                continue

            if end_time and entry.timestamp > end_time:
                continue

            if tags:
                # 检查是否包含所有指定标签
                if not all(tag in entry.tags for tag in tags):
                    continue

            filtered_entries.append(entry)

        # 按时间倒序排序
        filtered_entries.sort(key=lambda x: x.timestamp, reverse=True)

        # 应用分页
        return filtered_entries[offset : offset + limit]

    def get_agent_memory(self, agent_id: str, limit: int = 50) -> List[MemoryEntry]:
        """
        获取智能体的相关记忆

        Args:
            agent_id: 智能体ID
            limit: 返回条目限制

        Returns:
            相关内存条目列表
        """
        # 查询该智能体作为来源的条目
        agent_entries = self.query_memory(source_agent=agent_id, limit=limit)

        # 查询涉及该智能体的认知对齐事件
        alignment_entries = self.query_memory(
            entry_type=MemoryEntryType.COGNITIVE_ALIGNMENT, limit=limit // 2
        )

        # 过滤出涉及该智能体的对齐事件
        relevant_alignments = []
        for entry in alignment_entries:
            if "involved_agents" in entry.content and agent_id in entry.content["involved_agents"]:
                relevant_alignments.append(entry)

        # 合并结果
        all_entries = agent_entries + relevant_alignments

        # 按时间排序并去重
        unique_entries = {}
        for entry in all_entries:
            unique_entries[entry.entry_id] = entry

        sorted_entries = sorted(unique_entries.values(), key=lambda x: x.timestamp, reverse=True)

        return sorted_entries[:limit]

    def get_system_state_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取系统状态转换历史

        Args:
            limit: 返回条目限制

        Returns:
            状态转换历史列表
        """
        state_entries = self.query_memory(entry_type=MemoryEntryType.STATE_TRANSITION, limit=limit)

        history = []
        for entry in state_entries:
            history.append(
                {
                    "timestamp": entry.timestamp,
                    "from_state": entry.content.get("from_state"),
                    "to_state": entry.content.get("to_state"),
                    "trigger_agent": entry.source_agent,
                    "reason": entry.content.get("transition_reason", ""),
                    "hamming_distance": entry.content.get("hamming_distance"),
                    "gray_code_compliant": entry.content.get("is_gray_code_compliant"),
                    "entry_id": entry.entry_id,
                }
            )

        return history

    def get_cognitive_alignment_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        获取认知对齐摘要

        Args:
            time_window_hours: 时间窗口（小时）

        Returns:
            对齐摘要
        """
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()

        alignment_entries = self.query_memory(
            entry_type=MemoryEntryType.COGNITIVE_ALIGNMENT,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        summary = {
            "total_alignments": len(alignment_entries),
            "alignment_by_type": {},
            "agents_involved": set(),
            "time_period": {"start": start_time, "end": end_time},
        }

        for entry in alignment_entries:
            alignment_type = entry.content.get("alignment_type", "unknown")

            # 统计按类型
            if alignment_type not in summary["alignment_by_type"]:
                summary["alignment_by_type"][alignment_type] = 0
            summary["alignment_by_type"][alignment_type] += 1

            # 收集涉及智能体
            agents = entry.content.get("involved_agents", [])
            summary["agents_involved"].update(agents)

        summary["agents_involved"] = list(summary["agents_involved"])

        return summary

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        获取内存统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_entries": 0,
            "entries_by_type": {},
            "entries_by_priority": {},
            "entries_by_agent": {},
            "recent_activity": {"last_hour": 0, "last_24_hours": 0, "last_7_days": 0},
        }

        try:
            if self.db_path:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 总条目数
                cursor.execute("SELECT COUNT(*) FROM memory_entries")
                stats["total_entries"] = cursor.fetchone()[0]

                # 按类型统计
                cursor.execute(
                    "SELECT entry_type, COUNT(*) FROM memory_entries GROUP BY entry_type"
                )
                for entry_type, count in cursor.fetchall():
                    stats["entries_by_type"][entry_type] = count

                # 按优先级统计
                cursor.execute("SELECT priority, COUNT(*) FROM memory_entries GROUP BY priority")
                for priority, count in cursor.fetchall():
                    stats["entries_by_priority"][priority] = count

                # 按智能体统计
                cursor.execute(
                    "SELECT source_agent, COUNT(*) FROM memory_entries GROUP BY source_agent ORDER BY COUNT(*) DESC LIMIT 10"
                )
                for agent, count in cursor.fetchall():
                    stats["entries_by_agent"][agent] = count

                # 最近活动
                now = datetime.now()

                # 最近1小时
                hour_ago = (now - timedelta(hours=1)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE timestamp >= ?", (hour_ago,)
                )
                stats["recent_activity"]["last_hour"] = cursor.fetchone()[0]

                # 最近24小时
                day_ago = (now - timedelta(days=1)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE timestamp >= ?", (day_ago,)
                )
                stats["recent_activity"]["last_24_hours"] = cursor.fetchone()[0]

                # 最近7天
                week_ago = (now - timedelta(days=7)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE timestamp >= ?", (week_ago,)
                )
                stats["recent_activity"]["last_7_days"] = cursor.fetchone()[0]

                conn.close()
            else:
                # 使用缓存数据
                stats["total_entries"] = len(self.recent_entries)

                for entry in self.recent_entries:
                    # 按类型统计
                    entry_type = entry.entry_type.value
                    if entry_type not in stats["entries_by_type"]:
                        stats["entries_by_type"][entry_type] = 0
                    stats["entries_by_type"][entry_type] += 1

                    # 按优先级统计
                    priority = entry.priority.value
                    if priority not in stats["entries_by_priority"]:
                        stats["entries_by_priority"][priority] = 0
                    stats["entries_by_priority"][priority] += 1

                    # 按智能体统计
                    agent = entry.source_agent
                    if agent not in stats["entries_by_agent"]:
                        stats["entries_by_agent"][agent] = 0
                    stats["entries_by_agent"][agent] += 1

                # 最近活动（基于缓存）
                now = datetime.now()
                hour_ago = (now - timedelta(hours=1)).isoformat()
                day_ago = (now - timedelta(days=1)).isoformat()
                week_ago = (now - timedelta(days=7)).isoformat()

                for entry in self.recent_entries:
                    if entry.timestamp >= hour_ago:
                        stats["recent_activity"]["last_hour"] += 1
                    if entry.timestamp >= day_ago:
                        stats["recent_activity"]["last_24_hours"] += 1
                    if entry.timestamp >= week_ago:
                        stats["recent_activity"]["last_7_days"] += 1

        except Exception as e:
            self.logger.error(f"获取内存统计失败: {e}")

        return stats

    def cleanup_old_entries(self, days_to_keep: int = 90):
        """
        清理旧的内存条目

        Args:
            days_to_keep: 保留天数
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        try:
            if self.db_path:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 删除旧条目
                cursor.execute("DELETE FROM memory_entries WHERE timestamp < ?", (cutoff_date,))
                deleted_count = cursor.rowcount

                conn.commit()
                conn.close()

                self.logger.info(f"清理了 {deleted_count} 个超过 {days_to_keep} 天的内存条目")
            else:
                # 清理缓存
                initial_count = len(self.recent_entries)
                self.recent_entries = [
                    entry for entry in self.recent_entries if entry.timestamp >= cutoff_date
                ]
                cleaned_count = initial_count - len(self.recent_entries)
                self.logger.info(f"清理了 {cleaned_count} 个超过 {days_to_keep} 天的缓存条目")

        except Exception as e:
            self.logger.error(f"清理旧条目失败: {e}")

    def export_memory(self, export_path: str, entry_ids: Optional[List[str]] = None):
        """
        导出内存条目

        Args:
            export_path: 导出文件路径
            entry_ids: 要导出的条目ID列表（为空则导出全部）
        """
        try:
            entries = []

            if entry_ids:
                # 导出指定条目
                for entry_id in entry_ids:
                    entry = self._get_entry_by_id(entry_id)
                    if entry:
                        entries.append(entry.to_dict())
            else:
                # 导出所有条目（限制数量）
                all_entries = self.query_memory(limit=10000)
                entries = [entry.to_dict() for entry in all_entries]

            # 保存到文件
            export_dir = Path(export_path).parent
            export_dir.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "export_time": datetime.now().isoformat(),
                        "entry_count": len(entries),
                        "entries": entries,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            self.logger.info(f"已导出 {len(entries)} 个内存条目到 {export_path}")

        except Exception as e:
            self.logger.error(f"导出内存失败: {e}")

    def _get_entry_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """根据ID获取条目"""
        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM memory_entries WHERE entry_id = ?", (entry_id,))
                row = cursor.fetchone()

                conn.close()

                if row:
                    entry_dict = {
                        "entry_id": row["entry_id"],
                        "entry_type": MemoryEntryType(row["entry_type"]),
                        "timestamp": row["timestamp"],
                        "priority": MemoryPriority(row["priority"]),
                        "source_agent": row["source_agent"],
                        "content": json.loads(row["content_json"]),
                        "tags": json.loads(row["tags_json"]),
                        "references": json.loads(row["references_json"]),
                        "metadata": json.loads(row["metadata_json"]),
                    }
                    return MemoryEntry.from_dict(entry_dict)

            except Exception as e:
                self.logger.error(f"根据ID查询条目失败: {e}")

        # 从缓存中查找
        for entry in self.recent_entries:
            if entry.entry_id == entry_id:
                return entry

        return None

    def close(self):
        """
        关闭内存管理器，清理资源

        注意：调用此方法后，内存管理器将不可用
        """
        # 停止异步写入线程
        if self.writer_running:
            self._stop_async_writer()

        self.logger.info("内存管理器已关闭")

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息

        Returns:
            性能统计字典
        """
        return {
            "performance_mode": self.performance_mode,
            "sync_write_count": self.sync_write_count,
            "async_write_count": self.async_write_count,
            "total_writes": self.sync_write_count + self.async_write_count,
            "queue_size": self.write_queue.qsize() if hasattr(self, "write_queue") else 0,
            "writer_running": self.writer_running,
            "writer_alive": self.writer_thread.is_alive() if self.writer_thread else False,
            "cached_entries": len(self.recent_entries),
            "max_cached_entries": self.max_cached_entries,
        }

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.close()
        except:
            pass  # 忽略清理过程中的错误


def test_memory_manager():
    """测试内存管理器"""
    print("=== MAREF内存管理器测试 ===")

    # 创建内存管理器
    memory_manager = MAREFMemoryManager()

    print("✅ 内存管理器创建成功")

    # 测试记录状态转换
    print("\n=== 测试记录状态转换 ===")
    transition_id = memory_manager.record_state_transition(
        from_state="000000",
        to_state="000001",
        trigger_agent="coordinator",
        transition_reason="系统初始化",
    )
    print(f"状态转换记录ID: {transition_id}")

    # 测试记录智能体行动
    print("\n=== 测试记录智能体行动 ===")
    action_id = memory_manager.record_agent_action(
        agent_id="executor_001",
        agent_type="executor",
        action_type="task_execution",
        action_details={"task_id": "task_123", "command": "run_test"},
        result={"success": True, "output": "测试通过"},
    )
    print(f"智能体行动记录ID: {action_id}")

    # 测试记录智能体决策
    print("\n=== 测试记录智能体决策 ===")
    decision_id = memory_manager.record_agent_decision(
        agent_id="critic_001",
        agent_type="critic",
        decision_type="quality_assessment",
        decision_data={"score": 85, "feedback": "质量良好"},
        rationale="基于测试覆盖率和代码复杂度评估",
    )
    print(f"智能体决策记录ID: {decision_id}")

    # 测试记录系统事件
    print("\n=== 测试记录系统事件 ===")
    event_id = memory_manager.record_system_event(
        event_type="system_start",
        event_data={"version": "1.0.0", "components": "all"},
        severity="info",
        source="system_boot",
    )
    print(f"系统事件记录ID: {event_id}")

    # 测试记录认知对齐
    print("\n=== 测试记录认知对齐 ===")
    alignment_id = memory_manager.record_cognitive_alignment(
        alignment_type="state_awareness",
        involved_agents=["coordinator", "executor", "critic"],
        alignment_data={"aligned_state": "000001", "consensus_level": 0.95},
        alignment_result={"success": True, "aligned_agents": 3},
    )
    print(f"认知对齐记录ID: {alignment_id}")

    # 测试查询内存
    print("\n=== 测试查询内存 ===")
    entries = memory_manager.query_memory(limit=5)
    print(f"查询到 {len(entries)} 个条目:")
    for i, entry in enumerate(entries, 1):
        print(f"{i}. [{entry.entry_type.value}] {entry.source_agent} - {entry.timestamp[:19]}")

    # 测试获取系统状态历史
    print("\n=== 测试获取系统状态历史 ===")
    state_history = memory_manager.get_system_state_history(limit=3)
    print(f"状态转换历史 ({len(state_history)} 条):")
    for i, transition in enumerate(state_history, 1):
        print(
            f"{i}. {transition['from_state']} → {transition['to_state']} by {transition['trigger_agent']}"
        )

    # 测试获取智能体记忆
    print("\n=== 测试获取智能体记忆 ===")
    agent_memory = memory_manager.get_agent_memory("coordinator", limit=3)
    print(f"coordinator 相关记忆 ({len(agent_memory)} 条):")
    for i, entry in enumerate(agent_memory, 1):
        print(f"{i}. [{entry.entry_type.value}] {entry.timestamp[:19]}")

    # 测试获取认知对齐摘要
    print("\n=== 测试获取认知对齐摘要 ===")
    alignment_summary = memory_manager.get_cognitive_alignment_summary()
    print(f"认知对齐摘要:")
    print(f"  总对齐次数: {alignment_summary['total_alignments']}")
    print(f"  对齐类型分布: {alignment_summary['alignment_by_type']}")
    print(f"  涉及智能体: {alignment_summary['agents_involved']}")

    # 测试获取内存统计
    print("\n=== 测试获取内存统计 ===")
    stats = memory_manager.get_memory_statistics()
    print(f"内存统计:")
    print(f"  总条目数: {stats['total_entries']}")
    print(f"  条目类型分布: {stats['entries_by_type']}")
    print(f"  最近活动: {stats['recent_activity']}")

    # 测试导出内存
    print("\n=== 测试导出内存 ===")
    import tempfile

    temp_dir = tempfile.gettempdir()
    export_path = f"{temp_dir}/maref_memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    memory_manager.export_memory(export_path, entry_ids=[transition_id, action_id, decision_id])
    print(f"内存已导出到: {export_path}")

    print("\n=== 测试完成 ===")
    print("MAREF内存管理器功能验证通过")


if __name__ == "__main__":
    test_memory_manager()
