#!/usr/bin/env python3
"""
Revenue Ledger - 收益账本

记录技能合作社的三方分账（开发者、平台、社区）。
提供本地可审计的收益记录，支持后续链上结算。
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RevenueEntryStatus(Enum):
    """收益条目状态"""

    RECORDED = "recorded"  # 已记录
    PENDING_SETTLEMENT = "pending_settlement"  # 待结算
    SETTLED = "settled"  # 已结算
    CANCELLED = "cancelled"  # 已取消


@dataclass
class RevenueSplit:
    """收益分账配置"""

    developer: float  # 开发者分成比例 (0-1)
    platform: float  # 平台分成比例 (0-1)
    community: float  # 社区分成比例 (0-1)

    def validate(self) -> Tuple[bool, str]:
        """验证分账比例总和是否为1"""
        total = self.developer + self.platform + self.community
        if abs(total - 1.0) > 0.0001:
            return False, f"分账比例总和不为1: {total:.4f}"
        return True, ""


@dataclass
class RevenueEntry:
    """收益账本条目"""

    entry_id: str  # 条目唯一ID
    skill_id: str  # 技能ID
    developer_id: str  # 开发者ID
    task_id: Optional[str] = None  # 关联任务ID

    # 财务信息
    amount: float = 0.0  # 总收益金额（元）
    currency: str = "CNY"  # 货币

    # 分账详情
    split_config: Dict[str, float] = field(
        default_factory=lambda: {"developer": 0.7, "platform": 0.2, "community": 0.1}
    )
    developer_share: float = 0.0  # 开发者分账金额
    platform_share: float = 0.0  # 平台分账金额
    community_share: float = 0.0  # 社区分账金额

    # 状态
    status: str = RevenueEntryStatus.RECORDED.value
    settlement_tx_id: Optional[str] = None  # 结算交易ID

    # 时间戳
    created_at: str = ""
    settled_at: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def calculate_shares(self) -> None:
        """计算分账金额"""
        self.developer_share = self.amount * self.split_config.get("developer", 0.7)
        self.platform_share = self.amount * self.split_config.get("platform", 0.2)
        self.community_share = self.amount * self.split_config.get("community", 0.1)


class RevenueLedger:
    """收益账本"""

    def __init__(self, ledger_dir: Optional[str] = None):
        """
        初始化收益账本

        Args:
            ledger_dir: 账本数据目录，默认为 workspace/revenue_ledger
        """
        if ledger_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            self.ledger_dir = project_root / "workspace" / "revenue_ledger"
        else:
            self.ledger_dir = Path(ledger_dir)

        self.ledger_dir.mkdir(parents=True, exist_ok=True)

        # 内存索引
        self.entries: Dict[str, RevenueEntry] = {}
        self._load_existing_entries()

        logger.info(f"收益账本初始化完成，数据目录: {self.ledger_dir}")

    def _load_existing_entries(self) -> None:
        """加载现有的账本条目"""
        try:
            for json_file in self.ledger_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    entry = RevenueEntry(**data)
                    self.entries[entry.entry_id] = entry
                except Exception as e:
                    logger.warning(f"加载账本条目失败 {json_file}: {e}")

            logger.info(f"已加载 {len(self.entries)} 个现有账本条目")
        except Exception as e:
            logger.error(f"加载账本条目失败: {e}")

    def _save_entry(self, entry: RevenueEntry) -> None:
        """保存条目到文件"""
        try:
            entry_file = self.ledger_dir / f"revenue_{entry.entry_id}.json"
            entry_file.write_text(
                json.dumps(entry.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            logger.debug(f"收益条目已保存: {entry_file}")
        except Exception as e:
            logger.error(f"保存收益条目失败: {e}")
            raise

    def record_revenue(
        self,
        skill_id: str,
        developer_id: str,
        amount: float,
        split_config: Optional[Dict[str, float]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[RevenueEntry]]:
        """
        记录收益

        Args:
            skill_id: 技能ID
            developer_id: 开发者ID
            amount: 收益金额
            split_config: 分账配置，默认 {"developer": 0.7, "platform": 0.2, "community": 0.1}
            task_id: 关联任务ID
            metadata: 元数据

        Returns:
            (success, entry_id_or_error, revenue_entry)
        """
        try:
            # 验证金额
            if amount <= 0:
                return False, "收益金额必须为正数", None

            # 生成条目ID
            entry_id = f"rev_{uuid.uuid4().hex[:12]}"

            # 使用默认分账配置
            if split_config is None:
                split_config = {"developer": 0.7, "platform": 0.2, "community": 0.1}

            # 验证分账配置
            total = sum(split_config.values())
            if abs(total - 1.0) > 0.0001:
                return False, f"分账比例总和不为1: {total:.4f}", None

            # 创建条目
            entry = RevenueEntry(
                entry_id=entry_id,
                skill_id=skill_id,
                developer_id=developer_id,
                task_id=task_id,
                amount=amount,
                currency="CNY",
                split_config=split_config,
                status=RevenueEntryStatus.RECORDED.value,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )

            # 计算分账金额
            entry.calculate_shares()

            # 保存到内存和文件
            self.entries[entry_id] = entry
            self._save_entry(entry)

            logger.info(
                f"记录收益: {entry_id}, 技能: {skill_id}, 开发者: {developer_id}, 金额: {amount:.2f}"
            )

            return True, entry_id, entry

        except Exception as e:
            logger.error(f"记录收益失败: {e}")
            return False, str(e), None

    def get_entry(self, entry_id: str) -> Optional[RevenueEntry]:
        """获取收益条目"""
        return self.entries.get(entry_id)

    def list_entries(
        self,
        skill_id: Optional[str] = None,
        developer_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[RevenueEntry]:
        """
        列出收益条目（支持过滤）

        Args:
            skill_id: 按技能ID过滤
            developer_id: 按开发者ID过滤
            status: 按状态过滤
            start_date: 开始日期 (ISO格式)
            end_date: 结束日期 (ISO格式)
            limit: 返回条目数量限制

        Returns:
            收益条目列表
        """
        filtered = []

        for entry in self.entries.values():
            # 技能ID过滤
            if skill_id and entry.skill_id != skill_id:
                continue

            # 开发者ID过滤
            if developer_id and entry.developer_id != developer_id:
                continue

            # 状态过滤
            if status and entry.status != status:
                continue

            # 日期过滤
            if start_date:
                try:
                    entry_date = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if entry_date < start_dt:
                        continue
                except Exception:
                    pass

            if end_date:
                try:
                    entry_date = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    if entry_date > end_dt:
                        continue
                except Exception:
                    pass

            filtered.append(entry)

        # 按创建时间倒序排序
        filtered.sort(key=lambda x: x.created_at, reverse=True)

        return filtered[:limit]

    def get_summary(
        self,
        skill_id: Optional[str] = None,
        developer_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取收益摘要

        Returns:
            收益摘要字典
        """
        entries = self.list_entries(
            skill_id=skill_id,
            developer_id=developer_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        total_amount = 0.0
        total_developer = 0.0
        total_platform = 0.0
        total_community = 0.0
        entry_count = len(entries)

        for entry in entries:
            total_amount += entry.amount
            total_developer += entry.developer_share
            total_platform += entry.platform_share
            total_community += entry.community_share

        return {
            "entry_count": entry_count,
            "total_amount": total_amount,
            "total_developer": total_developer,
            "total_platform": total_platform,
            "total_community": total_community,
            "currency": "CNY",
            "filter": {
                "skill_id": skill_id,
                "developer_id": developer_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        }

    def mark_as_settled(
        self,
        entry_id: str,
        settlement_tx_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        标记为已结算

        Returns:
            (success, message)
        """
        if entry_id not in self.entries:
            return False, f"收益条目不存在: {entry_id}"

        entry = self.entries[entry_id]
        entry.status = RevenueEntryStatus.SETTLED.value
        entry.settlement_tx_id = settlement_tx_id
        entry.settled_at = datetime.now().isoformat()

        if metadata:
            entry.metadata.update(metadata)

        # 更新文件
        self._save_entry(entry)

        logger.info(f"收益条目 {entry_id} 标记为已结算，交易ID: {settlement_tx_id}")

        return True, "收益条目已标记为已结算"

    def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """
        删除收益条目（仅标记为取消）

        Returns:
            (success, message)
        """
        if entry_id not in self.entries:
            return False, f"收益条目不存在: {entry_id}"

        entry = self.entries[entry_id]
        entry.status = RevenueEntryStatus.CANCELLED.value

        # 更新文件
        self._save_entry(entry)

        logger.info(f"收益条目 {entry_id} 标记为已取消")

        return True, "收益条目已标记为已取消"


# ==================== 全局实例 ====================

_revenue_ledger_instance: Optional[RevenueLedger] = None


def get_revenue_ledger(ledger_dir: Optional[str] = None) -> RevenueLedger:
    """获取全局收益账本实例"""
    global _revenue_ledger_instance
    if _revenue_ledger_instance is None:
        _revenue_ledger_instance = RevenueLedger(ledger_dir)
    return _revenue_ledger_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== Revenue Ledger 测试 ===")

    ledger = RevenueLedger()

    print("\n1. 测试记录收益:")
    success, entry_id, entry = ledger.record_revenue(
        skill_id="openhuman-skill-matcher",
        developer_id="dev_001",
        amount=100.0,
        split_config={"developer": 0.6, "platform": 0.3, "community": 0.1},
        task_id="task_123",
        metadata={"execution_id": "exec_001"},
    )

    if success and entry:
        print(f"   条目ID: {entry_id}")
        print(f"   总金额: {entry.amount:.2f}")
        print(f"   开发者分账: {entry.developer_share:.2f}")
        print(f"   平台分账: {entry.platform_share:.2f}")
        print(f"   社区分账: {entry.community_share:.2f}")

    print("\n2. 测试记录另一个收益（使用默认分账）:")
    success2, entry_id2, entry2 = ledger.record_revenue(
        skill_id="opencli-scanner",
        developer_id="dev_002",
        amount=50.0,
        task_id="task_456",
    )

    if success2 and entry2:
        print(f"   条目ID: {entry_id2}")
        print(f"   分账配置: {entry2.split_config}")

    print("\n3. 测试查询:")
    entries = ledger.list_entries(developer_id="dev_001")
    print(f"   开发者 dev_001 的收益条目数: {len(entries)}")

    print("\n4. 测试摘要:")
    summary = ledger.get_summary()
    print(f"   总条目数: {summary['entry_count']}")
    print(f"   总收益: {summary['total_amount']:.2f}")
    print(f"   总开发者分账: {summary['total_developer']:.2f}")

    print("\n5. 测试标记为已结算:")
    if entry_id:
        success, msg = ledger.mark_as_settled(entry_id, settlement_tx_id="tx_123456")
        print(f"   结果: {success}, 消息: {msg}")

    print("\n=== 测试完成 ===")
