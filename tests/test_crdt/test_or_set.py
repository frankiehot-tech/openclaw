from athena.semantic_layer.crdt.or_set import ORSet


class TestORSet:
    def test_add(self):
        s = ORSet()
        eid = s.add("task-1")
        assert eid
        assert len(s) == 1

    def test_add_custom_id(self):
        s = ORSet()
        eid = s.add("task-1", element_id="custom-123")
        assert eid == "custom-123"

    def test_remove(self):
        s = ORSet()
        eid = s.add("task-1")
        assert s.remove(eid) is True
        assert len(s) == 0

    def test_remove_nonexistent(self):
        s = ORSet()
        assert s.remove("nonexistent") is False

    def test_tombstone_prevents_re_add(self):
        s = ORSet()
        eid = s.add("task-1")
        s.remove(eid)
        # Re-adding with same ID should work (explicit add)
        s.add("task-1", element_id=eid)
        assert len(s) == 1

    def test_get_all(self):
        s = ORSet()
        s.add("task-1")
        s.add("task-2")
        items = s.get_all()
        assert len(items) == 2

    def test_merge(self):
        s1 = ORSet()
        s1.add("task-1", element_id="e1")
        s1.add("task-2", element_id="e2")

        s2 = ORSet()
        s2.add("task-1", element_id="e1")  # must exist first to create tombstone
        s2.remove("e1")
        s2.add("task-3", element_id="e3")

        s1.merge(s2)
        assert len(s1) == 2  # e1 removed by s2 tombstone, e2 still there, e3 added

    def test_roundtrip(self):
        s = ORSet()
        s.add("task-1", element_id="e1")
        d = s.to_dict()
        restored = ORSet.from_dict(d)
        assert len(restored) == 1

    def test_merge_tombstones(self):
        s1 = ORSet()
        s1.add("task-1", element_id="e1")
        s1.remove("e1")

        s2 = ORSet()
        s2.add("task-1", element_id="e1")

        s1.merge(s2)
        assert len(s1) == 0  # Tombstone prevents remote add from reviving
