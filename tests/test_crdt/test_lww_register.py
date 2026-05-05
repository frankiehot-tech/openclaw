from athena.semantic_layer.crdt.lww_register import LWWRegister, LWWRegisterStore


class TestLWWRegister:
    def test_set_initial(self):
        reg = LWWRegister("fact1")
        assert reg.set("value1", 1.0, "agent-1") is True
        assert reg.get() == "value1"

    def test_set_higher_timestamp_wins(self):
        reg = LWWRegister("fact1")
        reg.set("old", 1.0, "agent-1")
        assert reg.set("new", 2.0, "agent-2") is True
        assert reg.get() == "new"

    def test_set_lower_timestamp_ignored(self):
        reg = LWWRegister("fact1")
        reg.set("current", 5.0, "agent-1")
        assert reg.set("stale", 3.0, "agent-2") is False
        assert reg.get() == "current"

    def test_set_same_timestamp_deterministic(self):
        reg = LWWRegister("fact1")
        reg.set("a", 5.0, "agent-x")
        reg.set("b", 5.0, "agent-y")
        assert reg.get() == "b"

    def test_roundtrip(self):
        reg = LWWRegister("fact1")
        reg.set("hello", 42.0, "agent-1")
        d = reg.to_dict()
        restored = LWWRegister.from_dict(d)
        assert restored.key == reg.key
        assert restored.get() == reg.get()
        assert restored.timestamp == reg.timestamp


class TestLWWRegisterStore:
    def test_set_and_get(self):
        store = LWWRegisterStore()
        store.set("key1", "val1", 1.0, "agent-1")
        assert store.get("key1") == "val1"

    def test_get_nonexistent(self):
        store = LWWRegisterStore()
        assert store.get("unknown") is None

    def test_merge_remote(self):
        local = LWWRegisterStore()
        local.set("x", "local_x", 1.0, "a")

        remote = {
            "x": {"key": "x", "value": "remote_x", "timestamp": 2.0, "source_agent": "b"},
            "y": {"key": "y", "value": "remote_y", "timestamp": 3.0, "source_agent": "b"},
        }
        updated = local.merge_remote(remote)
        assert updated == 2
        assert local.get("x") == "remote_x"
        assert local.get("y") == "remote_y"

    def test_to_dict(self):
        store = LWWRegisterStore()
        store.set("k", "v", 1.0, "a")
        d = store.to_dict()
        assert "k" in d
        assert d["k"]["value"] == "v"

    def test_size(self):
        store = LWWRegisterStore()
        store.set("a", 1, 1.0, "x")
        store.set("b", 2, 1.0, "x")
        assert store.size == 2
