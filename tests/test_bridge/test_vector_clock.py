from athena.semantic_layer.bridge.vector_clock import LamportClock, VectorClock


class TestLamportClock:
    def test_initial(self):
        lc = LamportClock()
        assert lc.time == 0

    def test_tick_increments(self):
        lc = LamportClock()
        assert lc.tick() == 1
        assert lc.tick() == 2
        assert lc.time == 2

    def test_witness_jumps_forward(self):
        lc = LamportClock()
        lc.tick()
        lc.tick()
        lc.witness(10)
        assert lc.time == 11

    def test_witness_no_backward(self):
        lc = LamportClock()
        lc.tick()
        lc.tick()
        lc.witness(10)
        lc.witness(3)
        assert lc.time >= 11

    def test_custom_initial(self):
        lc = LamportClock(initial=100)
        assert lc.tick() == 101


class TestVectorClock:
    def test_initial(self):
        vc = VectorClock("agent-1")
        snap = vc.snapshot
        assert snap == {"agent-1": 0}

    def test_tick_increments_self(self):
        vc = VectorClock("agent-1")
        vc.tick()
        vc.tick()
        assert vc.snapshot["agent-1"] == 2

    def test_merge(self):
        vc = VectorClock("agent-1")
        vc.tick()
        remote = {"agent-2": 5, "agent-3": 3}
        vc.merge(remote)
        assert vc.snapshot["agent-1"] == 2
        assert vc.snapshot["agent-2"] == 5
        assert vc.snapshot["agent-3"] == 3

    def test_is_concurrent(self):
        vc = VectorClock("A")
        vc.tick()
        remote = {"B": 1}
        assert vc.is_concurrent_with(remote) is True

    def test_happened_before_self(self):
        vc = VectorClock("A")
        vc.tick()
        snap1 = dict(vc.snapshot)
        vc.tick()
        snap2 = dict(vc.snapshot)
        vc2 = VectorClock("A")
        vc2._clock = snap1
        assert vc2.happened_before(snap2) is True

    def test_roundtrip(self):
        vc = VectorClock("agent-1")
        vc.tick()
        vc.tick()
        data = vc.to_dict()
        restored = VectorClock.from_dict(data)
        assert restored.agent_id == vc.agent_id
        assert restored.snapshot == vc.snapshot
