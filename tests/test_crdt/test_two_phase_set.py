from athena.semantic_layer.crdt.two_phase_set import TwoPhaseSet


class TestTwoPhaseSet:
    def test_add(self):
        s = TwoPhaseSet()
        assert s.add("rule-1") is True
        assert s.contains("rule-1") is True

    def test_remove(self):
        s = TwoPhaseSet()
        s.add("rule-1")
        assert s.remove("rule-1") is True
        assert s.contains("rule-1") is False

    def test_cannot_add_removed(self):
        s = TwoPhaseSet()
        s.add("rule-1")
        s.remove("rule-1")
        assert s.add("rule-1") is False

    def test_get_all(self):
        s = TwoPhaseSet()
        s.add("a")
        s.add("b")
        s.remove("a")
        assert s.get_all() == ["b"]

    def test_merge(self):
        s1 = TwoPhaseSet()
        s1.add("a")
        s1.add("b")

        s2 = TwoPhaseSet()
        s2.add("c")
        s2.remove("a")

        s1.merge(s2)
        assert "a" not in s1.get_all()  # removed by s2
        assert "b" in s1.get_all()
        assert "c" in s1.get_all()  # added by s2

    def test_roundtrip(self):
        s = TwoPhaseSet()
        s.add("a")
        s.add("b")
        s.remove("a")
        d = s.to_dict()
        restored = TwoPhaseSet.from_dict(d)
        assert restored.get_all() == s.get_all()

    def test_len(self):
        s = TwoPhaseSet()
        s.add("a")
        s.add("b")
        s.remove("a")
        assert len(s) == 1
