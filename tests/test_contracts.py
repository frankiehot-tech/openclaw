"""Basic tests for contracts module."""

import json

import pytest
from contracts.duplicate_analyzer import DuplicateAnalyzer
from contracts.quality_item import DataQualityItem


class TestDataQualityItem:
    def test_from_json_item_creates_valid_item(self):
        raw = {"id": "test_1", "title": "Test", "entry_stage": "build", "instruction_path": "/path/to/file"}
        item = DataQualityItem.from_json_item(raw, 0)
        assert item.id == "test_1"
        assert item.quality_score == 100.0
        assert len(item.issues) == 0

    def test_add_issue_reduces_score(self):
        item = DataQualityItem(id="test", data={}, hash="abc", quality_score=100.0)
        item.add_issue("critical problem", "critical")
        assert item.quality_score <= 70.0

    def test_validate_required_fields_missing(self):
        item = DataQualityItem(id="test", data={"id": "test"}, hash="abc", quality_score=100.0)
        result = item.validate_required_fields(["id", "title"])
        assert result is False
        assert any("title" in issue for issue in item.issues)

    def test_validate_required_fields_all_present(self):
        item = DataQualityItem(id="test", data={"id": "test", "title": "hello"}, hash="abc", quality_score=100.0)
        result = item.validate_required_fields(["id", "title"])
        assert result is True

    def test_to_dict_contains_expected_keys(self):
        item = DataQualityItem(id="test", data={"title": "hello"}, hash="abc", quality_score=85.0)
        d = item.to_dict()
        assert d["id"] == "test"
        assert d["quality_score"] == 85.0
        assert "data_summary" in d


class TestDuplicateAnalyzer:
    def test_analyze_no_duplicates(self):
        items = [
            {"id": "a", "title": "A", "entry_stage": "build", "instruction_path": "/a"},
            {"id": "b", "title": "B", "entry_stage": "build", "instruction_path": "/b"},
        ]
        analyzer = DuplicateAnalyzer()
        result = analyzer.analyze(items)
        assert result["total_items"] == 2
        assert result["duplicate_items"] == 0
        assert result["duplicate_rate"] == 0.0

    def test_analyze_with_duplicates(self):
        items = [
            {"id": "a", "title": "Same", "entry_stage": "build", "instruction_path": "/a"},
            {"id": "a", "title": "Same", "entry_stage": "build", "instruction_path": "/a"},
        ]
        analyzer = DuplicateAnalyzer()
        result = analyzer.analyze(items)
        assert result["duplicate_items"] >= 2
        assert result["duplicate_rate"] > 0

    def test_deduplicate_keep_first(self):
        items = [
            {"id": "a", "title": "Same", "entry_stage": "build", "instruction_path": "/a"},
            {"id": "a", "title": "Same", "entry_stage": "build", "instruction_path": "/a"},
        ]
        analyzer = DuplicateAnalyzer()
        deduped = analyzer.deduplicate(items, strategy="keep_first")
        assert len(deduped) == 1

    def test_deduplicate_no_duplicates_unchanged(self):
        items = [
            {"id": "a", "title": "A", "entry_stage": "build", "instruction_path": "/a"},
            {"id": "b", "title": "B", "entry_stage": "build", "instruction_path": "/b"},
        ]
        analyzer = DuplicateAnalyzer()
        deduped = analyzer.deduplicate(items)
        assert len(deduped) == 2


@pytest.fixture
def manifest_data():
    return {
        "manifest": {"name": "test", "version": "1.0"},
        "items": [
            {
                "id": "task_1",
                "title": "Build system",
                "entry_stage": "build",
                "instruction_path": "/path/to/instruction_1.md",
                "priority": 1,
            },
            {
                "id": "task_2",
                "title": "Review system",
                "entry_stage": "review",
                "instruction_path": "/path/to/instruction_2.md",
                "priority": 2,
            },
            {
                "id": "task_3",
                "title": "Test system",
                "entry_stage": "test",
                "instruction_path": "/path/to/instruction_3.md",
                "priority": 3,
            },
        ],
    }


@pytest.fixture
def manifest_path(tmp_path, manifest_data):
    p = tmp_path / "test_manifest.json"
    p.write_text(json.dumps(manifest_data))
    return str(p)


class TestDataQualityContract:
    def test_analyze_on_valid_manifest(self, manifest_path):
        from contracts.data_quality import DataQualityContract
        contract = DataQualityContract(manifest_path)
        loaded = contract.load_manifest(manifest_path)
        assert loaded is True
        result = contract.analyze_duplicates()
        assert result["total_entries"] == 3
        assert result["duplicate_ids_count"] == 0

    def test_validate_integrity(self, manifest_path):
        from contracts.data_quality import DataQualityContract
        contract = DataQualityContract(manifest_path)
        contract.load_manifest(manifest_path)
        result = contract.validate_data_integrity()
        assert "total_checked" in result or "passed_validation" in result
