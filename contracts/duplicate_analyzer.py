"""Duplicate Analyzer - duplicate detection and removal."""

import hashlib
import json
from typing import Any

from .quality_item import DataQualityItem


class DuplicateAnalyzer:
    def __init__(self) -> None:
        self.items: dict[str, DataQualityItem] = {}

    def analyze(self, raw_items: list[dict[str, Any]]) -> dict[str, Any]:
        quality_items = []
        for i, item in enumerate(raw_items):
            quality_items.append(DataQualityItem.from_json_item(item, i))

        hash_groups: dict[str, list[DataQualityItem]] = {}
        for qi in quality_items:
            hash_groups.setdefault(qi.hash, []).append(qi)

        duplicate_hashes = {h for h, group in hash_groups.items() if len(group) > 1}
        total_duplicates = sum(len(group) for h, group in hash_groups.items() if h in duplicate_hashes)

        for qi in quality_items:
            if qi.hash in duplicate_hashes:
                qi.duplicate_count = len(hash_groups[qi.hash])
                qi.duplicate_indices = [quality_items.index(x) for x in hash_groups[qi.hash]]
                qi.add_issue(f"重复条目 (hash={qi.hash[:8]})")

        return {
            "total_items": len(quality_items),
            "unique_items": len(hash_groups),
            "duplicate_items": total_duplicates,
            "duplicate_hashes": len(duplicate_hashes),
            "duplicate_rate": round(total_duplicates / len(quality_items) * 100, 2) if quality_items else 0.0,
            "hash_groups": hash_groups,
            "quality_items": quality_items,
        }

    def find_duplicates(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        seen_hashes: dict[str, int] = {}
        duplicates: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for i, item in enumerate(items):
            clean = {k: v for k, v in item.items() if k not in {"timestamp", "updated_at", "created_at", "index", "position"}}
            h = hashlib.md5(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:16]
            if h in seen_hashes:
                duplicates.setdefault(h, []).append((seen_hashes[h], items[seen_hashes[h]]))
                duplicates[h].append((i, item))
            else:
                seen_hashes[h] = i
        return {"duplicates": duplicates, "total_duplicates": sum(len(v) for v in duplicates.values())}

    def deduplicate(self, raw_items: list[dict[str, Any]], strategy: str = "keep_first") -> list[dict[str, Any]]:
        analysis = self.analyze(raw_items)
        keep: set[int] = set()
        seen_hashes: set[str] = set()
        for i, qi in enumerate(analysis["quality_items"]):
            if qi.hash not in seen_hashes:
                keep.add(i)
                seen_hashes.add(qi.hash)
            elif strategy == "keep_last":
                keep.remove(max([idx for idx, q in enumerate(analysis["quality_items"]) if q.hash == qi.hash and idx in keep]))
                keep.add(i)
        return [raw_items[i] for i in sorted(keep)]

    def _get_selection_criteria(self, item: DataQualityItem, strategy: str) -> str:
        if strategy == "keep_first":
            return "earliest"
        elif strategy == "keep_last":
            return "latest"
        elif strategy == "keep_highest_quality":
            return f"quality={item.quality_score:.1f}"
        return "unknown"
