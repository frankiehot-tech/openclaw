#!/usr/bin/env python3
"""
Improvement Loop - 最小改进回路

实现问题识别 → 优先级评估 → 改进实施 → 效果验证的闭环。
与 feedback_intake 和现有 queue/review/memory 体系集成。
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 导入反馈模块
try:
    from .feedback_intake import (
        FEEDBACK_SOURCE_INTERNAL,
        FEEDBACK_SOURCE_SYSTEM,
        FEEDBACK_STATE_ACCEPTED,
        FEEDBACK_STATE_FIXED,
        FEEDBACK_STATE_NEW,
        FEEDBACK_STATE_TRIAGED,
        FEEDBACK_STATE_VERIFIED,
        FeedbackItem,
        load_feedback,
        update_feedback_state,
    )
except ImportError:
    # 备用导入路径
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from feedback_intake import (
        FEEDBACK_SOURCE_INTERNAL,
        FEEDBACK_SOURCE_SYSTEM,
        FEEDBACK_STATE_ACCEPTED,
        FEEDBACK_STATE_FIXED,
        FEEDBACK_STATE_NEW,
        FEEDBACK_STATE_TRIAGED,
        FEEDBACK_STATE_VERIFIED,
        FeedbackItem,
        load_feedback,
        update_feedback_state,
    )

# 导入编排器（如果可用）
try:
    from .athena_orchestrator import get_orchestrator

    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    get_orchestrator = None

RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
IMPROVEMENT_DIR = RUNTIME_ROOT / ".openclaw" / "improvement_loop"
IMPROVEMENT_DIR.mkdir(parents=True, exist_ok=True)

# 改进阶段
IMPROVEMENT_PHASE_IDENTIFICATION = "identification"
IMPROVEMENT_PHASE_PRIORITIZATION = "prioritization"
IMPROVEMENT_PHASE_IMPLEMENTATION = "implementation"
IMPROVEMENT_PHASE_VALIDATION = "validation"

# 改进状态
IMPROVEMENT_STATUS_PENDING = "pending"
IMPROVEMENT_STATUS_ACTIVE = "active"
IMPROVEMENT_STATUS_COMPLETED = "completed"
IMPROVEMENT_STATUS_FAILED = "failed"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ImprovementItem:
    """改进条目"""

    improvement_id: str
    feedback_id: str  # 关联的反馈ID
    phase: str = IMPROVEMENT_PHASE_IDENTIFICATION
    status: str = IMPROVEMENT_STATUS_PENDING
    priority_score: float = 0.0  # 优先级得分（0-10）
    assigned_task_id: Optional[str] = None
    implementation_details: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImprovementItem":
        return cls(**data)


def generate_improvement_id() -> str:
    """生成改进ID"""
    import uuid
    from datetime import datetime

    return f"improvement_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"


def save_improvement(improvement: ImprovementItem) -> bool:
    """保存改进条目"""
    try:
        imp_path = IMPROVEMENT_DIR / f"{improvement.improvement_id}.json"
        with open(imp_path, "w", encoding="utf-8") as f:
            json.dump(improvement.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存改进条目失败: {e}")
        return False


def load_improvement(improvement_id: str) -> Optional[ImprovementItem]:
    """加载改进条目"""
    try:
        imp_path = IMPROVEMENT_DIR / f"{improvement_id}.json"
        if not imp_path.exists():
            return None
        with open(imp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ImprovementItem.from_dict(data)
    except Exception as e:
        logger.error(f"加载改进条目失败: {e}")
        return None


def create_improvement_from_feedback(feedback_id: str) -> Optional[ImprovementItem]:
    """从反馈创建改进条目（问题识别阶段）"""
    feedback = load_feedback(feedback_id)
    if not feedback:
        logger.warning(f"反馈不存在: {feedback_id}")
        return None

    # 检查是否已有改进条目
    improvements = list_improvements(feedback_id_filter=feedback_id)
    if improvements:
        logger.info(f"反馈已有改进条目: {improvements[0].improvement_id}")
        return improvements[0]

    improvement_id = generate_improvement_id()
    now = datetime.now().isoformat()

    improvement = ImprovementItem(
        improvement_id=improvement_id,
        feedback_id=feedback_id,
        phase=IMPROVEMENT_PHASE_IDENTIFICATION,
        status=IMPROVEMENT_STATUS_ACTIVE,
        priority_score=feedback.priority * 2.0,  # 将反馈优先级转换为分数
        created_at=now,
        updated_at=now,
        metadata={
            "feedback_title": feedback.title,
            "feedback_type": feedback.feedback_type,
            "feedback_source": feedback.source,
        },
    )

    if save_improvement(improvement):
        logger.info(f"创建改进条目: {improvement_id} for feedback {feedback_id}")
        return improvement
    return None


def prioritize_improvement(
    improvement_id: str, priority_score: float, criteria: Dict[str, Any]
) -> bool:
    """优先级评估阶段"""
    improvement = load_improvement(improvement_id)
    if not improvement:
        return False

    if improvement.phase != IMPROVEMENT_PHASE_IDENTIFICATION:
        logger.warning(f"改进条目不在识别阶段: {improvement.phase}")
        return False

    improvement.phase = IMPROVEMENT_PHASE_PRIORITIZATION
    improvement.priority_score = priority_score
    improvement.updated_at = datetime.now().isoformat()
    improvement.metadata["prioritization_criteria"] = criteria
    improvement.metadata["prioritized_at"] = datetime.now().isoformat()

    return save_improvement(improvement)


def implement_improvement(
    improvement_id: str,
    task_description: str,
    task_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """改进实施阶段 - 创建任务"""
    improvement = load_improvement(improvement_id)
    if not improvement:
        return False, None

    if improvement.phase != IMPROVEMENT_PHASE_PRIORITIZATION:
        logger.warning(f"改进条目不在优先级评估阶段: {improvement.phase}")
        return False, None

    task_id = None
    if ORCHESTRATOR_AVAILABLE and get_orchestrator:
        try:
            orchestrator = get_orchestrator()
            success, task_id, _ = orchestrator.create_task(
                stage="build",
                domain="engineering",
                description=task_description,
                dispatch_source="improvement_loop",
                dispatch_thread_id=improvement_id,
            )
            if not success:
                logger.warning(f"创建任务失败: {task_id}")
                task_id = None
        except Exception as e:
            logger.error(f"调用编排器失败: {e}")
            task_id = None

    improvement.phase = IMPROVEMENT_PHASE_IMPLEMENTATION
    improvement.assigned_task_id = task_id
    improvement.updated_at = datetime.now().isoformat()
    improvement.implementation_details = {
        "task_description": task_description,
        "task_metadata": task_metadata or {},
        "implementation_started_at": datetime.now().isoformat(),
    }

    if save_improvement(improvement):
        # 更新关联反馈状态为 accepted
        from .feedback_intake import accept_feedback

        accept_feedback(improvement.feedback_id, related_task_id=task_id)

        return True, task_id
    return False, None


def validate_improvement(
    improvement_id: str,
    validation_data: Dict[str, Any],
    artifact_paths: Optional[List[str]] = None,
) -> bool:
    """效果验证阶段"""
    improvement = load_improvement(improvement_id)
    if not improvement:
        return False

    if improvement.phase != IMPROVEMENT_PHASE_IMPLEMENTATION:
        logger.warning(f"改进条目不在实施阶段: {improvement.phase}")
        return False

    improvement.phase = IMPROVEMENT_PHASE_VALIDATION
    improvement.status = IMPROVEMENT_STATUS_COMPLETED
    improvement.updated_at = datetime.now().isoformat()
    improvement.completed_at = datetime.now().isoformat()
    improvement.validation_results = validation_data
    if artifact_paths:
        improvement.artifacts.extend(artifact_paths)

    # 沉淀到 memory
    try:
        memory_entry = {
            "improvement_id": improvement_id,
            "feedback_id": improvement.feedback_id,
            "phase": improvement.phase,
            "priority_score": improvement.priority_score,
            "validation_results": validation_data,
            "completed_at": improvement.completed_at,
            "metadata": improvement.metadata,
        }

        memory_dir = RUNTIME_ROOT / "memory" / "improvements"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / f"{improvement_id}.json"
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory_entry, f, ensure_ascii=False, indent=2)

        logger.info(f"改进结果沉淀到 memory: {memory_file}")
    except Exception as e:
        logger.error(f"沉淀到 memory 失败: {e}")

    if save_improvement(improvement):
        # 更新关联反馈状态为 verified
        from .feedback_intake import verify_feedback

        verify_feedback(
            improvement.feedback_id,
            verification_notes=json.dumps(validation_data, ensure_ascii=False),
        )
        return True
    return False


def list_improvements(
    phase_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    feedback_id_filter: Optional[str] = None,
    limit: int = 50,
) -> List[ImprovementItem]:
    """列出改进条目"""
    improvements = []
    for json_file in IMPROVEMENT_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            improvement = ImprovementItem.from_dict(data)

            if phase_filter and improvement.phase != phase_filter:
                continue
            if status_filter and improvement.status != status_filter:
                continue
            if feedback_id_filter and improvement.feedback_id != feedback_id_filter:
                continue

            improvements.append(improvement)
        except Exception as e:
            logger.warning(f"加载改进条目文件失败 {json_file}: {e}")
            continue

    # 按优先级得分和创建时间排序
    improvements.sort(key=lambda x: (-x.priority_score, x.created_at))
    return improvements[:limit]


def get_improvement_stats() -> Dict[str, Any]:
    """获取改进回路统计"""
    stats = {
        "total": 0,
        "by_phase": {
            IMPROVEMENT_PHASE_IDENTIFICATION: 0,
            IMPROVEMENT_PHASE_PRIORITIZATION: 0,
            IMPROVEMENT_PHASE_IMPLEMENTATION: 0,
            IMPROVEMENT_PHASE_VALIDATION: 0,
        },
        "by_status": {
            IMPROVEMENT_STATUS_PENDING: 0,
            IMPROVEMENT_STATUS_ACTIVE: 0,
            IMPROVEMENT_STATUS_COMPLETED: 0,
            IMPROVEMENT_STATUS_FAILED: 0,
        },
        "recent_completed": [],
    }

    for json_file in IMPROVEMENT_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            phase = data.get("phase", IMPROVEMENT_PHASE_IDENTIFICATION)
            status = data.get("status", IMPROVEMENT_STATUS_PENDING)

            stats["total"] += 1
            if phase in stats["by_phase"]:
                stats["by_phase"][phase] += 1
            if status in stats["by_status"]:
                stats["by_status"][status] += 1

            # 记录最近完成的改进
            if status == IMPROVEMENT_STATUS_COMPLETED:
                completed_at = data.get("completed_at")
                if completed_at:
                    stats["recent_completed"].append(
                        {
                            "improvement_id": data.get("improvement_id"),
                            "feedback_id": data.get("feedback_id"),
                            "completed_at": completed_at,
                            "priority_score": data.get("priority_score", 0),
                        }
                    )
        except Exception:
            continue

    # 按完成时间排序，取最近5个
    stats["recent_completed"].sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    stats["recent_completed"] = stats["recent_completed"][:5]

    return stats


def cleanup_old_improvements(days_to_keep: int = 30, only_completed: bool = True) -> Dict[str, int]:
    """清理旧的改进数据

    Args:
        days_to_keep: 保留最近多少天的数据
        only_completed: 是否只清理已完成的改进（True）或所有状态（False）
    Returns:
        删除的改进数量统计
    """
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days_to_keep)
    deleted = 0
    for json_file in IMPROVEMENT_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            created_str = data.get("created_at")
            if not created_str:
                continue
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created > cutoff:
                continue
            status = data.get("status", IMPROVEMENT_STATUS_PENDING)
            if only_completed and status != IMPROVEMENT_STATUS_COMPLETED:
                continue
            # 删除文件
            json_file.unlink()
            deleted += 1
        except Exception:
            continue
    return {"deleted_improvements": deleted}


def run_improvement_cycle() -> Dict[str, Any]:
    """运行改进回路周期（可定时触发）"""
    logger.info("开始改进回路周期运行")

    # 1. 识别新反馈
    from .feedback_intake import FEEDBACK_STATE_NEW, list_feedback

    new_feedbacks = list_feedback(state_filter=FEEDBACK_STATE_NEW)

    created = 0
    for feedback in new_feedbacks:
        improvement = create_improvement_from_feedback(feedback.feedback_id)
        if improvement:
            created += 1

    # 2. 评估优先级（模拟）
    improvements = list_improvements(
        phase_filter=IMPROVEMENT_PHASE_IDENTIFICATION,
        status_filter=IMPROVEMENT_STATUS_ACTIVE,
    )
    prioritized = 0
    for imp in improvements:
        # 简单优先级计算：基于反馈优先级和其他因素
        priority_score = imp.priority_score + 1.0  # 增加一点
        criteria = {"auto_prioritized": True, "cycle": datetime.now().isoformat()}
        if prioritize_improvement(imp.improvement_id, priority_score, criteria):
            prioritized += 1

    # 3. 实施改进（创建任务）
    improvements = list_improvements(
        phase_filter=IMPROVEMENT_PHASE_PRIORITIZATION,
        status_filter=IMPROVEMENT_STATUS_ACTIVE,
    )
    implemented = 0
    for imp in improvements:
        feedback = load_feedback(imp.feedback_id)
        if feedback:
            task_desc = f"改进: {feedback.title} - {feedback.description[:100]}..."
            success, task_id = implement_improvement(
                imp.improvement_id, task_desc, {"feedback_title": feedback.title}
            )
            if success:
                implemented += 1

    # 4. 验证效果（模拟 - 实际应由任务完成触发）
    improvements = list_improvements(
        phase_filter=IMPROVEMENT_PHASE_IMPLEMENTATION,
        status_filter=IMPROVEMENT_STATUS_ACTIVE,
    )
    validated = 0
    for imp in improvements:
        # 检查任务是否完成（简化）
        validation_data = {
            "validated_at": datetime.now().isoformat(),
            "validation_method": "auto_simulation",
            "result": "success",
        }
        if validate_improvement(imp.improvement_id, validation_data):
            validated += 1

    stats = get_improvement_stats()
    result = {
        "cycle_run_at": datetime.now().isoformat(),
        "new_feedbacks_processed": len(new_feedbacks),
        "improvements_created": created,
        "improvements_prioritized": prioritized,
        "improvements_implemented": implemented,
        "improvements_validated": validated,
        "stats": stats,
    }

    logger.info(f"改进回路周期完成: {result}")
    return result


if __name__ == "__main__":
    # 模块自测
    print("=== Improvement Loop 自测 ===")

    # 清理旧测试数据
    test_files = list(IMPROVEMENT_DIR.glob("*.json"))
    for f in test_files:
        f.unlink()

    # 需要先有测试反馈
    from feedback_intake import (
        FEEDBACK_SOURCE_INTERNAL,
        FEEDBACK_TYPE_BUG,
        create_feedback,
    )

    feedback = create_feedback(
        title="改进回路测试反馈",
        description="用于测试改进回路的反馈",
        source=FEEDBACK_SOURCE_INTERNAL,
        feedback_type=FEEDBACK_TYPE_BUG,
        priority=3,
    )

    if not feedback:
        print("创建测试反馈失败，跳过改进回路测试")
    else:
        print(f"创建测试反馈: {feedback.feedback_id}")

        # 测试创建改进条目
        improvement = create_improvement_from_feedback(feedback.feedback_id)
        print(f"创建改进条目: {'成功' if improvement else '失败'}")

        if improvement:
            # 测试优先级评估
            success = prioritize_improvement(
                improvement.improvement_id,
                priority_score=7.5,
                criteria={"test": True, "reason": "high_impact"},
            )
            print(f"优先级评估: {'成功' if success else '失败'}")

            # 测试实施改进
            success, task_id = implement_improvement(
                improvement.improvement_id, task_description="测试改进任务"
            )
            print(f"实施改进: {'成功' if success else '失败'}, 任务ID: {task_id}")

            # 测试验证
            success = validate_improvement(
                improvement.improvement_id,
                validation_data={
                    "test_result": "passed",
                    "metrics": {"accuracy": 0.95},
                },
            )
            print(f"验证改进: {'成功' if success else '失败'}")

    # 测试统计
    stats = get_improvement_stats()
    print(f"改进统计: {stats}")

    print("=== 自测完成 ===")
