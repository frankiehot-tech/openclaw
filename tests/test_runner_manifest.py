"""Tests for scripts/runner/manifest.py — item management"""

from scripts.runner.manifest import active_route_item_ids, manifest_item_depends_on


class TestManifestItemDependsOn:
    def test_no_depends_on(self):
        item = {"id": "task_1"}
        assert manifest_item_depends_on(item) == []

    def test_empty_depends_on(self):
        item = {"id": "task_1", "metadata": {"depends_on": []}}
        assert manifest_item_depends_on(item) == []

    def test_single_dependency(self):
        item = {"id": "task_2", "metadata": {"depends_on": ["task_1"]}}
        assert manifest_item_depends_on(item) == ["task_1"]

    def test_multiple_dependencies(self):
        item = {"id": "task_3", "metadata": {"depends_on": ["task_1", "task_2"]}}
        assert manifest_item_depends_on(item) == ["task_1", "task_2"]

    def test_non_list_depends_on(self):
        item = {"id": "task_1", "metadata": {"depends_on": "task_1"}}
        assert manifest_item_depends_on(item) == []

    def test_empty_spaces_stripped(self):
        item = {"id": "task_2", "metadata": {"depends_on": ["task_1", ""]}}
        assert manifest_item_depends_on(item) == ["task_1"]

    def test_no_metadata(self):
        item = {"id": "task_1"}
        assert manifest_item_depends_on(item) == []


class TestActiveRouteItemIds:
    def test_empty_state(self):
        assert active_route_item_ids({}) == []

    def test_single_active(self):
        state = {"items": {"task_1": {"status": "running"}}}
        assert active_route_item_ids(state) == ["task_1"]

    def test_multiple_states(self):
        state = {
            "items": {
                "task_1": {"status": "running"},
                "task_2": {"status": "pending"},
                "task_3": {"status": "completed"},
                "task_4": {"status": "running"},
                "task_5": {"status": "failed"},
            }
        }
        assert set(active_route_item_ids(state)) == {"task_1", "task_4"}

    def test_no_items_key(self):
        assert active_route_item_ids({"queue_id": "q1"}) == []
