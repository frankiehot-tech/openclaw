#!/usr/bin/env python3
"""
Feedback Intake Contract - 反馈收集契约

基于现有 workflow_state 体系，提供最小反馈闭环的状态跟踪。
状态流转: new → triaged → accepted → fixed → verified
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 复用 workflow_state 的存储根目录
RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
FEEDBACK_DIR = RUNTIME_ROOT / ".openclaw" / "feedback_state"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

# 反馈状态定义
FEEDBACK_STATE_NEW = "new"
FEEDBACK_STATE_TRIAGED = "triaged"
FEEDBACK_STATE_ACCEPTED = "accepted"
FEEDBACK_STATE_FIXED = "fixed"
FEEDBACK_STATE_VERIFIED = "verified"

VALID_FEEDBACK_STATES = {
    FEEDBACK_STATE_NEW,
    FEEDBACK_STATE_TRIAGED,
    FEEDBACK_STATE_ACCEPTED,
    FEEDBACK_STATE_FIXED,
    FEEDBACK_STATE_VERIFIED,
}

# 反馈来源
FEEDBACK_SOURCE_INTERNAL = "internal"  # 应用内反馈
FEEDBACK_SOURCE_MANUAL = "manual"  # 人工分诊
FEEDBACK_SOURCE_SYSTEM = "system"  # 系统自动生成

# 反馈类型
FEEDBACK_TYPE_BUG = "bug"
FEEDBACK_TYPE_FEATURE = "feature"
FEEDBACK_TYPE_ENHANCEMENT = "enhancement"
FEEDBACK_TYPE_QUESTION = "question"


@dataclass
class FeedbackItem:
    """反馈条目"""

    feedback_id: str
    state: str = FEEDBACK_STATE_NEW
    source: str = FEEDBACK_SOURCE_INTERNAL
    feedback_type: str = FEEDBACK_TYPE_BUG
    title: str = ""
    description: str = ""
    reporter: str = "unknown"
    priority: int = 0  # 0-5, 0最低
    created_at: str = ""
    updated_at: str = ""
    assigned_to: Optional[str] = None
    related_task_id: Optional[str] = None
    related_incident_id: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackItem":
        return cls(**data)


def generate_feedback_id() -> str:
    """生成反馈ID"""
    return f"feedback_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"


def save_feedback(feedback: FeedbackItem) -> bool:
    """保存反馈条目"""
    try:
        feedback_path = FEEDBACK_DIR / f"{feedback.feedback_id}.json"
        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump(feedback.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_feedback(feedback_id: str) -> Optional[FeedbackItem]:
    """加载反馈条目"""
    try:
        feedback_path = FEEDBACK_DIR / f"{feedback_id}.json"
        if not feedback_path.exists():
            return None
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return FeedbackItem.from_dict(data)
    except Exception:
        return None


def list_feedback(
    state_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    limit: int = 100,
) -> List[FeedbackItem]:
    """列出反馈条目"""
    feedbacks = []
    for json_file in FEEDBACK_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            feedback = FeedbackItem.from_dict(data)
            if state_filter and feedback.state != state_filter:
                continue
            if source_filter and feedback.source != source_filter:
                continue
            feedbacks.append(feedback)
        except Exception:
            continue
    # 按创建时间倒序
    feedbacks.sort(key=lambda x: x.created_at, reverse=True)
    return feedbacks[:limit]


def create_feedback(
    title: str,
    description: str,
    source: str = FEEDBACK_SOURCE_INTERNAL,
    feedback_type: str = FEEDBACK_TYPE_BUG,
    reporter: str = "unknown",
    priority: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[FeedbackItem]:
    """创建新反馈"""
    feedback_id = generate_feedback_id()
    now = datetime.now().isoformat()

    feedback = FeedbackItem(
        feedback_id=feedback_id,
        state=FEEDBACK_STATE_NEW,
        source=source,
        feedback_type=feedback_type,
        title=title,
        description=description,
        reporter=reporter,
        priority=priority,
        created_at=now,
        updated_at=now,
        metadata=metadata or {},
    )

    if save_feedback(feedback):
        return feedback
    return None


def update_feedback_state(
    feedback_id: str,
    new_state: str,
    assigned_to: Optional[str] = None,
    metadata_update: Optional[Dict[str, Any]] = None,
) -> bool:
    """更新反馈状态"""
    feedback = load_feedback(feedback_id)
    if not feedback:
        return False

    if new_state not in VALID_FEEDBACK_STATES:
        return False

    # 防止从verified状态回退（已验证是最终状态）
    if feedback.state == FEEDBACK_STATE_VERIFIED:
        return False

    feedback.state = new_state
    feedback.updated_at = datetime.now().isoformat()
    if assigned_to is not None:
        feedback.assigned_to = assigned_to
    if metadata_update:
        feedback.metadata.update(metadata_update)

    return save_feedback(feedback)


def triage_feedback(feedback_id: str, priority: int, assigned_to: Optional[str] = None) -> bool:
    """分诊反馈（new → triaged）"""
    feedback = load_feedback(feedback_id)
    if not feedback or feedback.state != FEEDBACK_STATE_NEW:
        return False

    feedback.state = FEEDBACK_STATE_TRIAGED
    feedback.priority = priority
    feedback.updated_at = datetime.now().isoformat()
    if assigned_to:
        feedback.assigned_to = assigned_to

    return save_feedback(feedback)


def accept_feedback(feedback_id: str, related_task_id: Optional[str] = None) -> bool:
    """接受反馈（triaged → accepted）"""
    feedback = load_feedback(feedback_id)
    if not feedback or feedback.state != FEEDBACK_STATE_TRIAGED:
        return False

    feedback.state = FEEDBACK_STATE_ACCEPTED
    feedback.updated_at = datetime.now().isoformat()
    feedback.related_task_id = related_task_id

    return save_feedback(feedback)


def mark_fixed(feedback_id: str, artifact_paths: Optional[List[str]] = None) -> bool:
    """标记为已修复（accepted → fixed）"""
    feedback = load_feedback(feedback_id)
    if not feedback or feedback.state != FEEDBACK_STATE_ACCEPTED:
        return False

    feedback.state = FEEDBACK_STATE_FIXED
    feedback.updated_at = datetime.now().isoformat()
    if artifact_paths:
        feedback.artifacts.extend(artifact_paths)

    return save_feedback(feedback)


def verify_feedback(feedback_id: str, verification_notes: str = "") -> bool:
    """验证反馈（fixed → verified）"""
    feedback = load_feedback(feedback_id)
    if not feedback or feedback.state != FEEDBACK_STATE_FIXED:
        return False

    feedback.state = FEEDBACK_STATE_VERIFIED
    feedback.updated_at = datetime.now().isoformat()
    feedback.metadata["verification_notes"] = verification_notes
    feedback.metadata["verified_at"] = datetime.now().isoformat()

    return save_feedback(feedback)


def get_feedback_stats() -> Dict[str, int]:
    """获取反馈统计"""
    stats = {state: 0 for state in VALID_FEEDBACK_STATES}
    stats["total"] = 0

    for json_file in FEEDBACK_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = data.get("state", FEEDBACK_STATE_NEW)
            if state in stats:
                stats[state] += 1
            stats["total"] += 1
        except Exception:
            continue

    return stats


def cleanup_old_feedback(days_to_keep: int = 30, only_verified: bool = True) -> Dict[str, int]:
    """清理旧的反馈数据

    Args:
        days_to_keep: 保留最近多少天的数据
        only_verified: 是否只清理已验证的反馈（True）或所有状态（False）
    Returns:
        删除的反馈数量统计
    """
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days_to_keep)
    deleted = 0
    for json_file in FEEDBACK_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            created_str = data.get("created_at")
            if not created_str:
                continue
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created > cutoff:
                continue
            state = data.get("state", FEEDBACK_STATE_NEW)
            if only_verified and state != FEEDBACK_STATE_VERIFIED:
                continue
            # 删除文件
            json_file.unlink()
            deleted += 1
        except Exception:
            continue
    return {"deleted_feedbacks": deleted}


if __name__ == "__main__":
    # 模块自测
    print("=== Feedback Intake Contract 自测 ===")

    # 清理旧测试数据
    test_files = list(FEEDBACK_DIR.glob("feedback_*"))
    for f in test_files:
        f.unlink()

    # 测试创建反馈
    feedback = create_feedback(
        title="测试反馈标题",
        description="这是一个测试反馈描述",
        source=FEEDBACK_SOURCE_INTERNAL,
        feedback_type=FEEDBACK_TYPE_BUG,
        priority=2,
    )
    print(f"创建反馈: {'成功' if feedback else '失败'}")
    if feedback:
        print(f"  反馈ID: {feedback.feedback_id}")
        print(f"  状态: {feedback.state}")

    # 测试分诊
    if feedback:
        success = triage_feedback(feedback.feedback_id, priority=3, assigned_to="alice")
        print(f"分诊反馈: {'成功' if success else '失败'}")

    # 测试接受
    if feedback and success:
        success = accept_feedback(feedback.feedback_id, related_task_id="task_001")
        print(f"接受反馈: {'成功' if success else '失败'}")

    # 测试标记修复
    if feedback and success:
        success = mark_fixed(feedback.feedback_id, artifact_paths=["/path/to/fix.patch"])
        print(f"标记修复: {'成功' if success else '失败'}")

    # 测试验证
    if feedback and success:
        success = verify_feedback(feedback.feedback_id, verification_notes="测试验证通过")
        print(f"验证反馈: {'成功' if success else '失败'}")

    # 测试统计
    stats = get_feedback_stats()
    print(f"反馈统计: {stats}")

    print("=== 自测完成 ===")
