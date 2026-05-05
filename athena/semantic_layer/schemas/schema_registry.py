from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SchemaVersion:
    major: int
    minor: int
    patch: int = 0

    @classmethod
    def parse(cls, version_str: str) -> SchemaVersion:
        v = version_str.replace("men0.semantic.v", "").replace("semantic.v", "")
        parts = v.split(".")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )

    def __str__(self) -> str:
        if self.patch == 0 and self.minor == 0:
            return f"men0.semantic.v{self.major}"
        if self.patch == 0:
            return f"men0.semantic.v{self.major}.{self.minor}"
        return f"men0.semantic.v{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: SchemaVersion) -> bool:
        return self.major == other.major and self.minor >= other.minor

    def is_breaking_change_from(self, other: SchemaVersion) -> bool:
        return self.major != other.major

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


CURRENT_VERSION = "men0.semantic.v1.0"


class SchemaRegistry:
    def __init__(self):
        self._schemas: dict[str, dict] = {}
        self._version = SchemaVersion.parse(CURRENT_VERSION)
        self._deprecated: set[str] = set()
        self._added_in: dict[str, SchemaVersion] = {}

    def register(
        self,
        name: str,
        schema_class: type | None = None,
        *,
        added_in: str = CURRENT_VERSION,
    ) -> None:
        self._schemas[name] = {"class": schema_class, "added_in": added_in}
        if added_in != CURRENT_VERSION:
            self._added_in[name] = SchemaVersion.parse(added_in)

    def get(self, name: str) -> dict:
        return self._schemas.get(name, {})

    def list_registered(self) -> list[str]:
        return list(self._schemas.keys())

    def check_compatibility(self, message_version: str, schema_name: str) -> bool:
        msg_ver = SchemaVersion.parse(message_version)
        entry = self._schemas.get(schema_name)
        if not entry:
            return False
        current_ver = SchemaVersion.parse(entry.get("added_in", CURRENT_VERSION))
        return msg_ver.is_compatible_with(current_ver)

    def validate_schema_version(self, expected: str, actual: str) -> str | None:
        exp_ver = SchemaVersion.parse(expected)
        act_ver = SchemaVersion.parse(actual)

        if act_ver.major > exp_ver.major:
            return f"Schema version {actual} is ahead of expected {expected}. Downgrade required."
        if act_ver.major < exp_ver.major:
            return f"Schema version {actual} is too old. Minimum required: {expected}."
        if act_ver.minor > exp_ver.minor:
            logger.info("Schema %s is newer than expected (%s), fields may be ignored", actual, expected)
        return None

    def detect_version_conflict(self, incoming_versions: dict[str, str]) -> list[str]:
        conflicts = []
        for schema_name, incoming_ver in incoming_versions.items():
            if schema_name not in self._schemas:
                conflicts.append(f"Unknown schema: {schema_name}")
                continue
            expected = self._schemas[schema_name].get("added_in", CURRENT_VERSION)
            error = self.validate_schema_version(expected, incoming_ver)
            if error:
                conflicts.append(error)
        return conflicts

    @property
    def current_version(self) -> str:
        return str(self._version)

    @property
    def version_info(self) -> dict[str, Any]:
        return {
            "version": self.current_version,
            "schema_count": len(self._schemas),
            "schemas": {
                name: {
                    "added_in": info.get("added_in", CURRENT_VERSION),
                    "has_class": info["class"] is not None,
                }
                for name, info in self._schemas.items()
            },
        }
