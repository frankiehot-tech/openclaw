"""Data Quality Item - individual item quality representation."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataQualityItem:
    id: str
    data: dict[str, Any]
    hash: str
    quality_score: float = 0.0
    issues: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    duplicate_indices: list[int] = field(default_factory=list)

    @classmethod
    def from_json_item(cls, item: dict[str, Any], index: int) -> "DataQualityItem":
        item_id = str(item.get("id", f"unknown_{index}"))
        clean_data = cls._clean_data_for_hashing(item)
        data_str = json.dumps(clean_data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:16]
        return cls(id=item_id, data=item, hash=data_hash, quality_score=100.0, issues=[], duplicate_count=0, duplicate_indices=[index])

    @staticmethod
    def _clean_data_for_hashing(data: dict[str, Any]) -> dict[str, Any]:
        clean_data = data.copy()
        for field in {"timestamp", "updated_at", "created_at", "index", "position"}:
            clean_data.pop(field, None)
        return clean_data

    def add_issue(self, issue: str, severity: str = "warning"):
        formatted_issue = f"[{severity.upper()}] {issue}"
        self.issues.append(formatted_issue)
        if severity == "critical":
            self.quality_score -= 30
        elif severity == "warning":
            self.quality_score -= 10
        elif severity == "info":
            self.quality_score -= 5
        self.quality_score = max(0.0, self.quality_score)

    def validate_required_fields(self, required_fields: list[str]) -> bool:
        valid = True
        for field in required_fields:
            if field not in self.data or self.data[field] is None or self.data[field] == "":
                self.add_issue(f"必需字段缺失: {field}", "critical")
                valid = False
        return valid

    def validate_field_formats(self, format_rules: dict[str, str]) -> bool:
        valid = True
        for field, pattern in format_rules.items():
            if field in self.data:
                value = str(self.data[field])
                if not re.match(pattern, value):
                    self.add_issue(f"字段格式无效: {field} = {value[:50]}...", "warning")
                    valid = False
        return valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "hash": self.hash,
            "quality_score": self.quality_score,
            "issues": self.issues,
            "duplicate_count": self.duplicate_count,
            "duplicate_indices": self.duplicate_indices,
            "data_summary": {
                "keys": list(self.data.keys()),
                "title": self.data.get("title", "无标题")[:50],
                "entry_stage": self.data.get("entry_stage", "未知"),
            },
        }
