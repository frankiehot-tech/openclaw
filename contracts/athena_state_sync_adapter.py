"""
Athena状态同步适配器 - 将StateSyncContract适配到Athena队列系统

基于深度审计发现：
1. 状态管理分散：状态信息分散在Web界面、队列文件、manifest中，缺乏统一状态机
2. 数据一致性挑战：Manifest、队列状态、任务状态之间缺乏强一致性保证
3. 并发更新问题：多组件同时更新状态可能导致数据不一致

此适配器将StateSyncContract适配到Athena系统的具体文件结构和API。

Athena系统结构：
1. 队列状态文件：`/.openclaw/plan_queue/{queue_id}.json`
2. Manifest文件：`/.openclaw/plan_queue/{manifest_name}.json`
3. Web界面API：`/api/athena/queues` 和 `/api/athena/queues/items/{queue_id}/{task_id}/status`
4. 任务状态：存储在队列文件的items字段中

适配器设计：
1. 单一事实源：使用队列状态文件作为基础状态
2. 多队列支持：支持Athena系统的多个队列
3. 向后兼容：保持现有文件格式不变
4. 增量同步：只同步变更的状态字段
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .state_sync import StateSyncContract

logger = logging.getLogger(__name__)


class AthenaStateSyncAdapter(StateSyncContract):
    """Athena状态同步适配器 - 将StateSyncContract适配到Athena队列系统"""

    def __init__(self, queue_id: str, base_dir: str | None = None):
        """
        初始化Athena状态同步适配器

        参数:
        - queue_id: 队列ID（如'athena_queue', 'gene_management_queue'）
        - base_dir: 基础目录（默认为运行时根目录）
        """
        self.queue_id = queue_id

        # 确定基础目录
        if base_dir is None:
            # 默认使用运行时根目录
            runtime_root = os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw")
            base_dir = runtime_root

        self.base_dir = Path(base_dir)

        # 队列状态文件路径（单一事实源）
        state_file = self.base_dir / ".openclaw" / "plan_queue" / f"{queue_id}.json"

        # 初始化父类
        super().__init__(str(state_file))

        # Athena特定路径
        self.queue_state_dir = self.base_dir / ".openclaw" / "plan_queue"
        self.manifest_dir = self.base_dir / ".openclaw" / "plan_queue"
        self.web_api_base = "http://localhost:5001"  # 默认Web服务器地址

        logger.info(f"Athena状态同步适配器初始化: queue_id={queue_id}, state_file={state_file}")

    def _load_state(self) -> dict[str, Any]:
        """
        加载基础状态（重写父类方法）

        将Athena队列文件格式（items字段）转换为StateSyncContract格式（tasks字段）
        """
        try:
            queue_state_path = self.queue_state_dir / f"{self.queue_id}.json"
            if not queue_state_path.exists():
                logger.debug(f"队列状态文件不存在: {queue_state_path}")
                return {"tasks": {}}

            with open(queue_state_path, encoding="utf-8") as f:
                queue_data = json.load(f)

            # 转换Athena队列格式为StateSyncContract格式
            tasks = {}
            items = queue_data.get("items", {})

            for item_id, item_data in items.items():
                if isinstance(item_data, dict):
                    # 映射字段
                    task_state = {
                        "id": item_id,
                        "status": item_data.get("status", "pending"),
                        "title": item_data.get("title", ""),
                        "stage": item_data.get("stage", "build"),
                        "progress_percent": item_data.get("progress_percent", 0),
                        "created_at": item_data.get("created_at", ""),
                        "updated_at": item_data.get("updated_at", ""),
                        "finished_at": item_data.get("finished_at", ""),
                        "summary": item_data.get("summary", ""),
                        "error": item_data.get("error", ""),
                        "runner_pid": item_data.get("runner_pid"),
                        "instruction_path": item_data.get("instruction_path", ""),
                        "artifact_paths": item_data.get("artifact_paths", []),
                        "metadata": item_data.get("metadata", {}),
                    }
                    tasks[item_id] = task_state

            # 保留原始队列数据的其他字段
            state = {"tasks": tasks}
            for key, value in queue_data.items():
                if key != "items":
                    state[key] = value

            return state

        except Exception as e:
            logger.error(f"加载状态失败: {str(e)}")
            return {"tasks": {}}

    def _save_state(self, state: dict[str, Any]) -> bool:
        """
        保存基础状态（重写父类方法）

        将StateSyncContract格式（tasks字段）转换回Athena队列文件格式（items字段）
        """
        try:
            queue_state_path = self.queue_state_dir / f"{self.queue_id}.json"

            # 读取当前队列文件（保留现有结构）
            if queue_state_path.exists():
                with open(queue_state_path, encoding="utf-8") as f:
                    queue_data = json.load(f)
            else:
                queue_data = {}

            # 转换tasks字段回items格式
            tasks = state.get("tasks", {})
            items = {}

            for task_id, task_data in tasks.items():
                if isinstance(task_data, dict):
                    # 反向字段映射
                    item_data = {
                        "status": task_data.get("status", "pending"),
                        "title": task_data.get("title", ""),
                        "stage": task_data.get("stage", "build"),
                        "progress_percent": task_data.get("progress_percent", 0),
                        "created_at": task_data.get("created_at", ""),
                        "updated_at": task_data.get("updated_at", ""),
                        "finished_at": task_data.get("finished_at", ""),
                        "summary": task_data.get("summary", ""),
                        "error": task_data.get("error", ""),
                        "runner_pid": task_data.get("runner_pid"),
                        "instruction_path": task_data.get("instruction_path", ""),
                        "artifact_paths": task_data.get("artifact_paths", []),
                        "metadata": task_data.get("metadata", {}),
                    }
                    # 移除空字符串值
                    item_data = {k: v for k, v in item_data.items() if v not in [None, ""]}
                    items[task_id] = item_data

            # 更新items字段
            queue_data["items"] = items

            # 原子性写入：先写入临时文件，然后重命名
            temp_file = f"{queue_state_path}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)

            # 重命名（原子性操作）
            os.replace(temp_file, queue_state_path)
            return True

        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")
            return False

    def _load_queue_state(self) -> dict[str, Any]:
        """
        加载队列状态（从队列文件）

        返回:
        - 队列状态字典
        """
        try:
            queue_state_path = self.queue_state_dir / f"{self.queue_id}.json"
            if not queue_state_path.exists():
                logger.debug(f"队列状态文件不存在: {queue_state_path}")
                return {"tasks": {}}

            with open(queue_state_path, encoding="utf-8") as f:
                queue_data = json.load(f)

            # 转换Athena队列格式为StateSyncContract格式
            tasks = {}
            items = queue_data.get("items", {})

            for item_id, item_data in items.items():
                if isinstance(item_data, dict):
                    # 映射字段
                    task_state = {
                        "id": item_id,
                        "status": item_data.get("status", "pending"),
                        "title": item_data.get("title", ""),
                        "stage": item_data.get("stage", "build"),
                        "progress_percent": item_data.get("progress_percent", 0),
                        "created_at": item_data.get("created_at", ""),
                        "updated_at": item_data.get("updated_at", ""),
                        "finished_at": item_data.get("finished_at", ""),
                        "summary": item_data.get("summary", ""),
                        "error": item_data.get("error", ""),
                        "runner_pid": item_data.get("runner_pid"),
                        "instruction_path": item_data.get("instruction_path", ""),
                        "artifact_paths": item_data.get("artifact_paths", []),
                        "metadata": item_data.get("metadata", {}),
                    }
                    tasks[item_id] = task_state

            return {"tasks": tasks}

        except Exception as e:
            logger.error(f"加载队列状态失败: {str(e)}")
            return {"tasks": {}}

    def _load_manifest_state(self) -> dict[str, Any]:
        """
        加载manifest状态（从manifest文件）

        Athena系统可能有多个manifest文件，这里加载与队列相关的manifest。
        优先执行队列：openhuman_aiplan_priority_execution_20260414.json
        构建优先级队列：openhuman_aiplan_build_priority_20260328.json

        返回:
        - manifest状态字典
        """
        try:
            # 查找与当前队列相关的manifest文件
            manifest_files = [
                "openhuman_aiplan_priority_execution_20260414.json",
                "openhuman_aiplan_build_priority_20260328.json",
                f"{self.queue_id}_manifest.json",
            ]

            manifest_path = None
            for manifest_file in manifest_files:
                potential_path = self.manifest_dir / manifest_file
                if potential_path.exists():
                    manifest_path = potential_path
                    break

            if not manifest_path:
                logger.debug(f"未找到manifest文件: {self.queue_id}")
                return {"tasks": {}}

            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)

            # 转换manifest格式为StateSyncContract格式
            tasks = {}

            # manifest可能有不同的结构
            if isinstance(manifest_data, dict):
                # 检查是否有items字段
                items = manifest_data.get("items", [])
                if isinstance(items, list):
                    for item in items:
                        item_id = item.get("id")
                        if item_id:
                            task_state = {
                                "id": item_id,
                                "title": item.get("title", ""),
                                "stage": item.get("entry_stage", "build"),
                                "instruction_path": item.get("instruction_path", ""),
                                "created_at": item.get("created_at", datetime.now().isoformat()),
                                "status": "pending",  # manifest中的任务默认为pending
                                "source": "manifest",
                            }
                            tasks[item_id] = task_state

            return {"tasks": tasks}

        except Exception as e:
            logger.error(f"加载manifest状态失败: {str(e)}")
            return {"tasks": {}}

    def _load_web_state(self) -> dict[str, Any]:
        """
        加载Web界面状态（从Web缓存或API）

        通过Web API获取队列状态。

        返回:
        - Web状态字典
        """
        try:
            # 尝试通过Web API获取状态
            api_url = f"{self.web_api_base}/api/athena/queues/{self.queue_id}"

            # 注意：Web API需要认证，这里可能需要token
            headers = {}

            # 尝试从环境变量或文件获取token
            token = os.getenv("OPENCLAW_WEB_TOKEN")
            if token:
                headers["X-OpenClaw-Token"] = token

            response = requests.get(api_url, headers=headers, timeout=5)

            if response.status_code == 200:
                web_data = response.json()

                # 转换Web API格式为StateSyncContract格式
                tasks = {}

                # 根据实际API响应结构解析
                items = web_data.get("items", [])
                if isinstance(items, list):
                    for item in items:
                        item_id = item.get("id")
                        if item_id:
                            task_state = {
                                "id": item_id,
                                "status": item.get("status", "pending"),
                                "title": item.get("title", ""),
                                "progress_percent": item.get("progress_percent", 0),
                                "updated_at": item.get("updated_at", ""),
                                "source": "web",
                            }
                            tasks[item_id] = task_state

                return {"tasks": tasks}
            else:
                logger.debug(f"Web API请求失败: {response.status_code}")
                return {"tasks": {}}

        except requests.exceptions.RequestException as e:
            logger.debug(f"Web API连接失败: {str(e)}")
            return {"tasks": {}}
        except Exception as e:
            logger.error(f"加载Web状态失败: {str(e)}")
            return {"tasks": {}}

    def _sync_to_queue(self, task_id: str, updates: dict[str, Any]):
        """
        同步状态到队列文件

        参数:
        - task_id: 任务ID
        - updates: 要更新的字段
        """
        try:
            queue_state_path = self.queue_state_dir / f"{self.queue_id}.json"
            if not queue_state_path.exists():
                logger.warning(f"队列状态文件不存在，无法同步: {queue_state_path}")
                return

            # 读取当前队列状态
            with open(queue_state_path, encoding="utf-8") as f:
                queue_data = json.load(f)

            # 确保items字段存在
            if "items" not in queue_data:
                queue_data["items"] = {}

            # 获取或创建任务条目
            if task_id not in queue_data["items"]:
                queue_data["items"][task_id] = {}

            # 应用更新（字段映射）
            for key, value in updates.items():
                # 特殊字段映射
                if key == "status":
                    queue_data["items"][task_id]["status"] = value
                elif key == "progress_percent":
                    queue_data["items"][task_id]["progress_percent"] = value
                elif key == "summary":
                    queue_data["items"][task_id]["summary"] = value
                elif key == "error":
                    queue_data["items"][task_id]["error"] = value
                elif key == "finished_at":
                    queue_data["items"][task_id]["finished_at"] = value
                elif key == "runner_pid":
                    queue_data["items"][task_id]["runner_pid"] = value
                else:
                    # 其他字段直接复制
                    queue_data["items"][task_id][key] = value

            # 更新更新时间
            queue_data["items"][task_id]["updated_at"] = datetime.now().isoformat()

            # 保存队列状态
            with open(queue_state_path, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"同步到队列文件成功: task_id={task_id}, queue={self.queue_id}")

        except Exception as e:
            logger.error(f"同步到队列文件失败: {str(e)}")

    def _sync_to_manifest(self, task_id: str, updates: dict[str, Any]):
        """
        同步状态到manifest文件

        注意：manifest通常只包含任务定义，不包含运行时状态。
         这里只更新manifest中的状态相关字段。

        参数:
        - task_id: 任务ID
        - updates: 要更新的字段
        """
        try:
            # 查找相关的manifest文件
            manifest_files = [
                "openhuman_aiplan_priority_execution_20260414.json",
                "openhuman_aiplan_build_priority_20260328.json",
                f"{self.queue_id}_manifest.json",
            ]

            manifest_path = None
            for manifest_file in manifest_files:
                potential_path = self.manifest_dir / manifest_file
                if potential_path.exists():
                    manifest_path = potential_path
                    break

            if not manifest_path:
                logger.debug(f"未找到manifest文件，无法同步: {self.queue_id}")
                return

            # 读取manifest
            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)

            # 查找并更新任务
            updated = False

            if isinstance(manifest_data, dict) and "items" in manifest_data:
                items = manifest_data["items"]
                if isinstance(items, list):
                    for item in items:
                        if item.get("id") == task_id:
                            # 只更新manifest中允许的字段
                            if "status" in updates:
                                item["status"] = updates["status"]
                            if "progress_percent" in updates:
                                item["progress_percent"] = updates["progress_percent"]
                            if "updated_at" in updates:
                                item["updated_at"] = updates["updated_at"]

                            updated = True
                            break

            # 如果找到并更新了任务，保存manifest
            if updated:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)

                logger.debug(
                    f"同步到manifest成功: task_id={task_id}, manifest={manifest_path.name}"
                )
            else:
                logger.debug(f"在manifest中未找到任务: {task_id}")

        except Exception as e:
            logger.error(f"同步到manifest失败: {str(e)}")

    def _sync_to_web(self, task_id: str, updates: dict[str, Any]):
        """
        同步状态到Web界面

        通过Web API更新Web界面状态。

        参数:
        - task_id: 任务ID
        - updates: 要更新的字段
        """
        try:
            # Web API端点
            api_url = (
                f"{self.web_api_base}/api/athena/queues/items/{self.queue_id}/{task_id}/status"
            )

            # 准备请求头
            headers = {"Content-Type": "application/json"}
            token = os.getenv("OPENCLAW_WEB_TOKEN")
            if token:
                headers["X-OpenClaw-Token"] = token

            # 准备请求体
            payload = {
                "task_id": task_id,
                "queue_id": self.queue_id,
                "updates": updates,
                "timestamp": datetime.now().isoformat(),
            }

            # 发送PUT请求更新状态
            response = requests.put(api_url, json=payload, headers=headers, timeout=5)

            if response.status_code in [200, 201]:
                logger.debug(f"同步到Web界面成功: task_id={task_id}, 响应={response.status_code}")
            else:
                logger.warning(
                    f"同步到Web界面失败: task_id={task_id}, 状态码={response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            logger.debug(f"Web API连接失败: {str(e)}")
        except Exception as e:
            logger.error(f"同步到Web界面失败: {str(e)}")

    def get_queue_state(self) -> dict[str, Any]:
        """
        获取队列状态（原始Athena格式）

        返回:
        - 原始队列状态
        """
        try:
            queue_state_path = self.queue_state_dir / f"{self.queue_id}.json"
            if not queue_state_path.exists():
                return {}

            with open(queue_state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"获取队列状态失败: {str(e)}")
            return {}


# 辅助函数：创建适配器实例
def create_athena_state_sync_adapter(queue_id: str) -> AthenaStateSyncAdapter:
    """
    创建Athena状态同步适配器实例

    参数:
    - queue_id: 队列ID

    返回:
    - AthenaStateSyncAdapter实例
    """
    return AthenaStateSyncAdapter(queue_id)


# 全局适配器缓存
_adapter_cache: dict[str, AthenaStateSyncAdapter] = {}


def get_athena_state_sync_adapter(queue_id: str) -> AthenaStateSyncAdapter:
    """
    获取Athena状态同步适配器（缓存单例）

    参数:
    - queue_id: 队列ID

    返回:
    - AthenaStateSyncAdapter实例
    """
    if queue_id not in _adapter_cache:
        _adapter_cache[queue_id] = create_athena_state_sync_adapter(queue_id)

    return _adapter_cache[queue_id]
