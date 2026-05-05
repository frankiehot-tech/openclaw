from athena.semantic_layer.schemas.schema_registry import (
    SchemaRegistry,
    SchemaVersion,
)


class TestSchemaVersion:
    def test_parse_v1(self):
        v = SchemaVersion.parse("men0.semantic.v1")
        assert v.major == 1
        assert v.minor == 0
        assert str(v) == "men0.semantic.v1"

    def test_parse_v1_2(self):
        v = SchemaVersion.parse("men0.semantic.v1.2")
        assert v.major == 1
        assert v.minor == 2
        assert str(v) == "men0.semantic.v1.2"

    def test_parse_short_form(self):
        v = SchemaVersion.parse("semantic.v2")
        assert v.major == 2

    def test_is_compatible_same_major(self):
        v1 = SchemaVersion.parse("men0.semantic.v1")
        v2 = SchemaVersion.parse("men0.semantic.v1.5")
        assert v2.is_compatible_with(v1) is True

    def test_not_compatible_different_major(self):
        v1 = SchemaVersion.parse("men0.semantic.v1")
        v2 = SchemaVersion.parse("men0.semantic.v2")
        assert v2.is_compatible_with(v1) is False

    def test_is_breaking_change(self):
        v1 = SchemaVersion.parse("men0.semantic.v1")
        v2 = SchemaVersion.parse("men0.semantic.v2")
        assert v2.is_breaking_change_from(v1) is True

    def test_not_breaking_same_major(self):
        v1 = SchemaVersion.parse("men0.semantic.v1.0")
        v2 = SchemaVersion.parse("men0.semantic.v1.5")
        assert v2.is_breaking_change_from(v1) is False


class TestSchemaRegistry:
    def setup_method(self):
        self.reg = SchemaRegistry()

    def test_current_version(self):
        assert self.reg.current_version == "men0.semantic.v1"

    def test_register_and_get(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        assert self.reg.get("intent") is not None

    def test_list_registered(self):
        self.reg.register("intent")
        self.reg.register("state")
        assert len(self.reg.list_registered()) == 2

    def test_check_compatibility_v1(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        assert self.reg.check_compatibility("men0.semantic.v1", "intent") is True

    def test_check_compatibility_v1_5_against_v1(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        assert self.reg.check_compatibility("men0.semantic.v1.5", "intent") is True

    def test_check_compatibility_v2_against_v1(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        assert self.reg.check_compatibility("men0.semantic.v2", "intent") is False

    def test_unknown_schema(self):
        assert self.reg.check_compatibility("men0.semantic.v1", "unknown") is False

    def test_validate_version_major_ahead(self):
        error = self.reg.validate_schema_version("men0.semantic.v1", "men0.semantic.v2")
        assert error is not None
        assert "ahead" in error

    def test_validate_version_major_behind(self):
        error = self.reg.validate_schema_version("men0.semantic.v2", "men0.semantic.v1")
        assert error is not None
        assert "too old" in error

    def test_validate_version_match(self):
        assert self.reg.validate_schema_version("men0.semantic.v1", "men0.semantic.v1") is None

    def test_validate_version_newer_minor(self):
        assert self.reg.validate_schema_version("men0.semantic.v1", "men0.semantic.v1.3") is None

    def test_detect_version_conflict(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        conflicts = self.reg.detect_version_conflict({"intent": "men0.semantic.v2"})
        assert len(conflicts) == 1

    def test_detect_no_conflict(self):
        self.reg.register("intent", added_in="men0.semantic.v1")
        conflicts = self.reg.detect_version_conflict({"intent": "men0.semantic.v1"})
        assert len(conflicts) == 0

    def test_detect_unknown_schema(self):
        conflicts = self.reg.detect_version_conflict({"unknown": "men0.semantic.v1"})
        assert len(conflicts) == 1

    def test_version_info(self):
        self.reg.register("intent")
        info = self.reg.version_info
        assert info["version"] == "men0.semantic.v1"
        assert info["schema_count"] == 1
