"""Feature flags — toggle features on/off with rollback safety."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    name: str
    enabled: bool
    rollout_percent: int = 100
    description: str = ""
    owner: str = ""
    created: str = ""


class FeatureFlagStore:
    """Persistent feature flag storage."""

    def __init__(self, flags_path: str | Path | None = None) -> None:
        self._path = Path(flags_path or "config/feature_flags.json")
        self._flags: dict[str, FeatureFlag] = {}

    def load(self) -> dict[str, FeatureFlag]:
        if self._path.exists():
            with open(self._path) as f:
                data = json.load(f)
            for name, cfg in data.items():
                self._flags[name] = FeatureFlag(
                    name=name,
                    enabled=cfg.get("enabled", False),
                    rollout_percent=cfg.get("rollout_percent", 100),
                    description=cfg.get("description", ""),
                    owner=cfg.get("owner", ""),
                    created=cfg.get("created", ""),
                )
        return dict(self._flags)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            name: {
                "enabled": f.enabled,
                "rollout_percent": f.rollout_percent,
                "description": f.description,
                "owner": f.owner,
                "created": f.created,
            }
            for name, f in self._flags.items()
        }
        with open(self._path, "w") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def set_flag(self, name: str, enabled: bool | None = None, rollout_percent: int | None = None) -> None:
        if name not in self._flags:
            self._flags[name] = FeatureFlag(name=name, enabled=False)
        flag = self._flags[name]
        if enabled is not None:
            flag.enabled = enabled
        if rollout_percent is not None:
            flag.rollout_percent = max(0, min(100, rollout_percent))
        self.save()

    def is_enabled(self, name: str, user_id: str | None = None) -> bool:
        flag = self._flags.get(name)
        if not flag or not flag.enabled:
            return False
        if flag.rollout_percent >= 100:
            return True
        if user_id:
            bucket = hash(user_id) % 100
            return bucket < flag.rollout_percent
        return False

    def get_all(self) -> dict[str, FeatureFlag]:
        return dict(self._flags)
