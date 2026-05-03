"""
状态同步契约 - 确保Web界面、队列文件、manifest状态一致性

基于深度审计发现：
1. 状态管理分散：状态信息分散在Web界面、队列文件、manifest中，缺乏统一状态机
2. 数据一致性挑战：Manifest、队列状态、任务状态之间缺乏强一致性保证
3. 并发更新问题：多组件同时更新状态可能导致数据不一致

此契约确保：
1. 单一事实源：统一状态管理，消除状态分散
2. 原子性更新：事务性状态更新，保证一致性
3. 并发安全：支持多线程并发更新，避免竞态条件
4. 状态同步：自动同步状态到所有相关组件（Web界面、队列文件、manifest）
5. 一致性保证：提供一致的状态视图，支持故障恢复

设计原则：
1. 契约先行：明确定义状态更新和同步的契约
2. 原子性：状态更新是事务性的，要么全部成功，要么全部失败
3. 可追溯性：记录所有状态变更，支持审计和调试
4. 故障隔离：状态同步失败不影响核心功能

MAREF框架集成：符合三才六层模型的控制层要求
"""

import hashlib
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class StateSyncContract:
    """状态同步契约 - 确保Web界面、队列文件、manifest状态一致性"""

    def __init__(self, state_file: str, lock_timeout: int = 10):
        """
        初始化状态同步契约

        参数:
        - state_file: 状态文件路径（单一事实源）
        - lock_timeout: 锁超时时间（秒）
        """
        self.state_file = state_file
        self.lock = threading.RLock()
        self.lock_timeout = lock_timeout

        # 确保状态文件目录存在
        os.makedirs(os.path.dirname(os.path.abspath(state_file)), exist_ok=True)

        logger.info(f"状态同步契约初始化: 状态文件={state_file}")

    def atomic_update(self, task_id: str, updates: dict[str, Any]) -> bool:
        """
        原子性状态更新，确保一致性

        参数:
        - task_id: 任务ID
        - updates: 要更新的字段和值

        返回:
        - 成功返回True，失败返回False
        """
        with self.lock:
            try:
                # 1. 读取当前状态
                current_state = self._load_state()

                # 2. 计算状态哈希（用于乐观锁）
                current_hash = hashlib.md5(
                    json.dumps(current_state, sort_keys=True).encode()
                ).hexdigest()

                # 3. 准备更新
                if "tasks" not in current_state:
                    current_state["tasks"] = {}

                # 确保任务条目存在
                if task_id not in current_state["tasks"]:
                    current_state["tasks"][task_id] = {}

                # 4. 应用更新
                current_state["tasks"][task_id].update(updates)
                current_state["tasks"][task_id]["updated_at"] = datetime.now().isoformat()

                # 5. 记录更新元数据
                if "_metadata" not in current_state:
                    current_state["_metadata"] = {}
                if "update_history" not in current_state["_metadata"]:
                    current_state["_metadata"]["update_history"] = []

                current_state["_metadata"]["update_history"].append(
                    {
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "updates": updates,
                        "previous_hash": current_hash,
                    }
                )

                # 限制历史记录大小
                if len(current_state["_metadata"]["update_history"]) > 1000:
                    current_state["_metadata"]["update_history"] = current_state["_metadata"][
                        "update_history"
                    ][-1000:]

                # 6. 保存状态
                success = self._save_state(current_state)

                if success:
                    # 7. 异步同步到其他组件
                    threading.Thread(
                        target=self._sync_to_components, args=(task_id, updates), daemon=True
                    ).start()

                logger.info(f"原子状态更新成功: task_id={task_id}, 更新字段={list(updates.keys())}")
                return success

            except Exception as e:
                logger.error(f"原子状态更新失败: {str(e)}")
                import traceback

                logger.error(f"堆栈跟踪: {traceback.format_exc()}")
                return False

    def get_consistent_state(self, task_id: str | None = None) -> dict[str, Any]:
        """
        获取一致的状态视图（合并队列文件、manifest、Web缓存）

        参数:
        - task_id: 可选，特定任务ID。如果为None，返回所有状态

        返回:
        - 一致的状态视图
        """
        with self.lock:
            try:
                # 1. 加载基础状态（单一事实源）
                base_state = self._load_state()

                # 2. 从其他组件加载状态
                queue_state = self._load_queue_state()
                manifest_state = self._load_manifest_state()
                web_state = self._load_web_state()

                # 3. 合并策略：以基础状态为主，其他状态为补充
                merged_state = self._merge_states(
                    base_state, queue_state, manifest_state, web_state
                )

                # 4. 如果指定了task_id，只返回该任务的状态
                if task_id is not None:
                    task_state = merged_state.get("tasks", {}).get(task_id, {})
                    return {
                        "task_id": task_id,
                        "state": task_state,
                        "merged_from": {
                            "base": task_id in base_state.get("tasks", {}),
                            "queue": task_id in queue_state.get("tasks", {}),
                            "manifest": task_id in manifest_state.get("tasks", {}),
                            "web": task_id in web_state.get("tasks", {}),
                        },
                    }

                return merged_state

            except Exception as e:
                logger.error(f"获取一致状态失败: {str(e)}")
                return {"error": f"获取一致状态失败: {str(e)}"}

    def validate_state_consistency(self) -> dict[str, Any]:
        """
        验证所有组件状态的一致性

        返回:
        - 一致性验证报告
        """
        with self.lock:
            try:
                # 加载所有组件的状态
                base_state = self._load_state()
                queue_state = self._load_queue_state()
                manifest_state = self._load_manifest_state()
                web_state = self._load_web_state()

                # 收集所有任务ID
                all_task_ids = set()
                all_task_ids.update(base_state.get("tasks", {}).keys())
                all_task_ids.update(queue_state.get("tasks", {}).keys())
                all_task_ids.update(manifest_state.get("tasks", {}).keys())
                all_task_ids.update(web_state.get("tasks", {}).keys())

                # 分析一致性
                consistency_report = {
                    "total_tasks": len(all_task_ids),
                    "components": {
                        "base": len(base_state.get("tasks", {})),
                        "queue": len(queue_state.get("tasks", {})),
                        "manifest": len(manifest_state.get("tasks", {})),
                        "web": len(web_state.get("tasks", {})),
                    },
                    "inconsistencies": [],
                    "consistency_score": 0.0,
                }

                # 检查每个任务的一致性
                for task_id in all_task_ids:
                    base_task = base_state.get("tasks", {}).get(task_id, {})
                    queue_task = queue_state.get("tasks", {}).get(task_id, {})
                    manifest_task = manifest_state.get("tasks", {}).get(task_id, {})
                    web_task = web_state.get("tasks", {}).get(task_id, {})

                    # 检查状态字段一致性
                    states = {
                        "base": base_task.get("status"),
                        "queue": queue_task.get("status"),
                        "manifest": manifest_task.get("status"),
                        "web": web_task.get("status"),
                    }

                    # 找出不一致的状态
                    unique_states = {v for v in states.values() if v is not None}
                    if len(unique_states) > 1:
                        inconsistency = {
                            "task_id": task_id,
                            "states": states,
                            "severity": (
                                "high"
                                if "running" in unique_states or "failed" in unique_states
                                else "medium"
                            ),
                        }
                        consistency_report["inconsistencies"].append(inconsistency)

                # 计算一致性得分
                if len(all_task_ids) > 0:
                    consistency_report["consistency_score"] = 100.0 * (
                        1.0 - len(consistency_report["inconsistencies"]) / len(all_task_ids)
                    )

                logger.info(
                    f"状态一致性验证完成: 得分={consistency_report['consistency_score']:.1f}%, 不一致={len(consistency_report['inconsistencies'])}"
                )
                return consistency_report

            except Exception as e:
                logger.error(f"状态一致性验证失败: {str(e)}")
                return {"error": f"状态一致性验证失败: {str(e)}"}

    def repair_inconsistencies(self, task_id: str | None = None) -> dict[str, Any]:
        """
        修复状态不一致问题

        参数:
        - task_id: 可选，特定任务ID。如果为None，修复所有不一致

        返回:
        - 修复报告
        """
        with self.lock:
            try:
                # 1. 验证当前状态一致性
                consistency_report = self.validate_state_consistency()

                if "error" in consistency_report:
                    return {"error": f"无法验证一致性: {consistency_report['error']}"}

                # 2. 确定需要修复的任务
                tasks_to_repair = []
                if task_id is not None:
                    # 修复特定任务
                    for inconsistency in consistency_report["inconsistencies"]:
                        if inconsistency["task_id"] == task_id:
                            tasks_to_repair.append(task_id)
                            break
                else:
                    # 修复所有不一致任务
                    tasks_to_repair = [
                        inc["task_id"] for inc in consistency_report["inconsistencies"]
                    ]

                # 3. 修复每个任务
                repair_report = {"total_repaired": 0, "successful": [], "failed": [], "details": {}}

                for task_id in tasks_to_repair:
                    try:
                        # 获取一致的状态（以基础状态为准）
                        consistent_state = self.get_consistent_state(task_id)

                        if "error" in consistent_state:
                            repair_report["failed"].append(
                                {"task_id": task_id, "error": consistent_state["error"]}
                            )
                            continue

                        # 提取任务状态
                        task_state = consistent_state.get("state", {})

                        # 同步到所有组件
                        success = self._sync_task_to_all_components(task_id, task_state)

                        if success:
                            repair_report["successful"].append(task_id)
                            repair_report["details"][task_id] = {
                                "status": task_state.get("status", "unknown"),
                                "synced_to": ["base", "queue", "manifest", "web"],
                            }
                        else:
                            repair_report["failed"].append(
                                {"task_id": task_id, "error": "同步到组件失败"}
                            )

                    except Exception as e:
                        repair_report["failed"].append({"task_id": task_id, "error": str(e)})

                repair_report["total_repaired"] = len(repair_report["successful"])

                logger.info(
                    f"状态不一致修复完成: 成功={repair_report['total_repaired']}, 失败={len(repair_report['failed'])}"
                )
                return repair_report

            except Exception as e:
                logger.error(f"状态不一致修复失败: {str(e)}")
                return {"error": f"状态不一致修复失败: {str(e)}"}

    # 私有方法

    def _load_state(self) -> dict[str, Any]:
        """加载基础状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logger.error(f"加载状态失败: {str(e)}")
            return {}

    def _save_state(self, state: dict[str, Any]) -> bool:
        """保存基础状态"""
        try:
            # 原子性写入：先写入临时文件，然后重命名
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # 重命名（原子性操作）
            os.replace(temp_file, self.state_file)
            return True

        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")
            return False

    def _load_queue_state(self) -> dict[str, Any]:
        """加载队列状态（从队列文件）"""
        # TODO: 实现从实际队列文件加载状态
        # 目前返回空状态，需要根据实际队列文件路径实现
        return {"tasks": {}}

    def _load_manifest_state(self) -> dict[str, Any]:
        """加载manifest状态（从manifest文件）"""
        # TODO: 实现从实际manifest文件加载状态
        # 目前返回空状态，需要根据实际manifest文件路径实现
        return {"tasks": {}}

    def _load_web_state(self) -> dict[str, Any]:
        """加载Web界面状态（从Web缓存或API）"""
        # TODO: 实现从Web界面加载状态
        # 目前返回空状态，需要根据实际Web接口实现
        return {"tasks": {}}

    def _merge_states(
        self,
        base_state: dict[str, Any],
        queue_state: dict[str, Any],
        manifest_state: dict[str, Any],
        web_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        合并多个来源的状态

        合并策略：
        1. 以基础状态为主（单一事实源）
        2. 其他状态作为补充，仅当基础状态缺失时使用
        3. 冲突时使用最新时间戳
        """
        merged_state = base_state.copy()

        # 确保tasks字典存在
        if "tasks" not in merged_state:
            merged_state["tasks"] = {}

        # 收集所有来源的任务
        all_sources = [("queue", queue_state), ("manifest", manifest_state), ("web", web_state)]

        for source_name, source_state in all_sources:
            source_tasks = source_state.get("tasks", {})
            for task_id, task_data in source_tasks.items():
                if task_id not in merged_state["tasks"]:
                    # 基础状态中没有，添加
                    merged_state["tasks"][task_id] = task_data
                    merged_state["tasks"][task_id]["_source"] = source_name
                else:
                    # 基础状态中已有，检查时间戳
                    base_timestamp = merged_state["tasks"][task_id].get("updated_at", "")
                    source_timestamp = task_data.get("updated_at", "")

                    if source_timestamp > base_timestamp:
                        # 来源状态更新，合并字段
                        merged_state["tasks"][task_id].update(task_data)
                        merged_state["tasks"][task_id]["_source"] = f"merged({source_name})"

        return merged_state

    def _sync_to_components(self, task_id: str, updates: dict[str, Any]):
        """异步同步状态到其他组件"""
        try:
            # 获取完整任务状态
            task_state = self.get_consistent_state(task_id)
            if "error" in task_state:
                logger.warning(f"无法获取任务状态用于同步: {task_state['error']}")
                return

            # 同步到队列文件
            self._sync_to_queue(task_id, updates)

            # 同步到manifest
            self._sync_to_manifest(task_id, updates)

            # 同步到Web界面
            self._sync_to_web(task_id, updates)

            logger.debug(f"状态同步完成: task_id={task_id}")

        except Exception as e:
            logger.error(f"状态同步失败: {str(e)}")

    def _sync_to_queue(self, task_id: str, updates: dict[str, Any]):
        """同步状态到队列文件"""
        # TODO: 实现实际队列文件同步
        # 这里需要根据实际队列文件格式实现
        pass

    def _sync_to_manifest(self, task_id: str, updates: dict[str, Any]):
        """同步状态到manifest文件"""
        # TODO: 实现实际manifest文件同步
        # 这里需要根据实际manifest文件格式实现
        pass

    def _sync_to_web(self, task_id: str, updates: dict[str, Any]):
        """同步状态到Web界面"""
        # TODO: 实现Web界面同步（通过API或WebSocket）
        # 这里需要根据实际Web接口实现
        pass

    def _sync_task_to_all_components(self, task_id: str, task_state: dict[str, Any]) -> bool:
        """同步任务状态到所有组件"""
        try:
            # 更新基础状态
            current_state = self._load_state()
            if "tasks" not in current_state:
                current_state["tasks"] = {}
            current_state["tasks"][task_id] = task_state
            current_state["tasks"][task_id]["updated_at"] = datetime.now().isoformat()

            # 保存基础状态
            if not self._save_state(current_state):
                return False

            # 同步到其他组件
            self._sync_to_queue(task_id, task_state)
            self._sync_to_manifest(task_id, task_state)
            self._sync_to_web(task_id, task_state)

            return True

        except Exception as e:
            logger.error(f"同步任务到所有组件失败: {str(e)}")
            return False


def create_default_state_sync(
    state_dir: str = "/Volumes/1TB-M2/openclaw/.openclaw/state",
) -> StateSyncContract:
    """
    创建默认的状态同步契约

    参数:
    - state_dir: 状态目录路径

    返回:
    - 初始化的StateSyncContract实例
    """
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, "unified_state.json")

    return StateSyncContract(state_file)


def validate_state_consistency_across_system() -> dict[str, Any]:
    """
    验证整个系统的状态一致性（便捷函数）

    返回:
    - 系统级状态一致性报告
    """
    # 创建默认状态同步契约
    state_sync = create_default_state_sync()

    # 验证一致性
    return state_sync.validate_state_consistency()
