"""Skillos v0.2.0 — Skill Markdown format standardization and lifecycle."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass, field
from enum import Enum, auto


class SkillCategory(Enum):
    CORE = auto()
    DOMAIN = auto()
    TOOL = auto()
    COORDINATION = auto()
    META = auto()
    EXPERIMENTAL = auto()


class SkillLifecycle(Enum):
    DRAFT = auto()
    REVIEW = auto()
    APPROVED = auto()
    ACTIVE = auto()
    DEPRECATED = auto()
    RETIRED = auto()


@dataclass
class SkillFrontmatter:
    name: str
    description: str
    category: SkillCategory
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    lifecycle: SkillLifecycle = SkillLifecycle.DRAFT
    signature: str = ""

    def sign(self, secret: str) -> str:
        payload = f"{self.name}|{self.version}|{self.category.name}|{self.lifecycle.name}"
        self.signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256,
        ).hexdigest()
        return self.signature

    def verify(self, secret: str) -> bool:
        expected = hashlib.sha256(
            f"{self.name}|{self.version}|{self.category.name}|{self.lifecycle.name}".encode()
        ).hexdigest()
        return hmac.compare_digest(expected, self.signature)


class SkillParser:
    """Parses and validates SKILL.md files."""

    YAML_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

    @classmethod
    def parse(cls, content: str) -> tuple[SkillFrontmatter, str] | None:
        match = cls.YAML_PATTERN.search(content)
        if not match:
            return None
        import yaml
        try:
            frontmatter_data = yaml.safe_load(match.group(1))
        except Exception:  # noqa: B904
            return None
        frontmatter = SkillFrontmatter(
            name=frontmatter_data.get("name", ""),
            description=frontmatter_data.get("description", ""),
            category=SkillCategory[frontmatter_data.get("category", "EXPERIMENTAL").upper()],
            version=frontmatter_data.get("version", "1.0.0"),
            author=frontmatter_data.get("author", ""),
            tags=frontmatter_data.get("tags", []),
            dependencies=frontmatter_data.get("dependencies", []),
            capabilities=frontmatter_data.get("capabilities", []),
            lifecycle=SkillLifecycle[frontmatter_data.get("lifecycle", "DRAFT").upper()],
        )
        body = content[match.end():].strip()
        return frontmatter, body

    @classmethod
    def validate(cls, frontmatter: SkillFrontmatter) -> list[str]:
        issues: list[str] = []
        if not frontmatter.name:
            issues.append("Missing skill name")
        if not frontmatter.description:
            issues.append("Missing description")
        if frontmatter.version and not re.match(r"^\d+\.\d+\.\d+$", frontmatter.version):
            issues.append(f"Invalid version format: {frontmatter.version}")
        return issues


class SkillRegistry:
    """Registers and discovers skills with semantic search."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillFrontmatter] = {}
        self._by_category: dict[SkillCategory, list[str]] = {c: [] for c in SkillCategory}
        self._by_tag: dict[str, list[str]] = {}

    def register(self, frontmatter: SkillFrontmatter, secret: str = "") -> None:
        if secret:
            frontmatter.sign(secret)
        self._skills[frontmatter.name] = frontmatter
        self._by_category[frontmatter.category].append(frontmatter.name)
        for tag in frontmatter.tags:
            self._by_tag.setdefault(tag, []).append(frontmatter.name)

    def get(self, name: str) -> SkillFrontmatter | None:
        return self._skills.get(name)

    def search(self, query: str, limit: int = 10) -> list[str]:
        query_lower = query.lower()
        scored: list[tuple[float, str]] = []
        for name, skill in self._skills.items():
            score = 0.0
            if query_lower in name.lower():
                score += 3.0
            if query_lower in skill.description.lower():
                score += 2.0
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 1.0
            for cap in skill.capabilities:
                if query_lower in cap.lower():
                    score += 1.5
            if score > 0:
                scored.append((score, name))
        scored.sort(key=lambda x: -x[0])
        return [name for _, name in scored[:limit]]

    def by_category(self, category: SkillCategory) -> list[str]:
        return list(self._by_category.get(category, []))

    def by_tag(self, tag: str) -> list[str]:
        return list(self._by_tag.get(tag, []))


class SkillRouter:
    """Routes tasks to appropriate skills based on intent and capability matching."""

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry()

    def route(self, intent: str, capability: str) -> str | None:
        if capability:
            matches = self.registry.search(capability, limit=3)
            if matches:
                return matches[0]
        return self._best_match(intent)

    def _best_match(self, intent: str) -> str | None:
        results = self.registry.search(intent, limit=1)
        return results[0] if results else None
