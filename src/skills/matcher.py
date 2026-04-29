"""Skill matcher — 技能匹配引擎。

Core functions:
  - geo_filter: 地理距离硬门槛
  - match_score: 40/30/20/10 加权评分
  - find_best_matches: 主入口（过滤 → 评分 → 排序 → Top N）
"""

from __future__ import annotations

from pydantic import BaseModel


class Skill(BaseModel):
    name: str
    category: str
    geo: tuple[float, float]
    price: float
    rating: float
    tags: list[str] = []


class MatchResult(BaseModel):
    skill: Skill
    score: float
    breakdown: dict


def _haversine_km(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Haversine formula — approximate great-circle distance in km."""
    import math

    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geo_filter(skill: Skill, user_geo: tuple[float, float], radius_km: float = 50.0) -> bool:
    """地理距离硬门槛。距离 > radius_km 返回 False。"""
    dist = _haversine_km(skill.geo, user_geo)
    return dist <= radius_km


def _calc_skill_match(skill: Skill, requirements: dict) -> float:
    req_cat = requirements.get("category", "")
    if not req_cat:
        return 100.0
    if skill.category == req_cat:
        return 100.0
    req_tags = set(requirements.get("tags", []))
    if not req_tags:
        return 50.0
    common = req_tags & set(skill.tags)
    return round(len(common) / len(req_tags) * 100, 2)


def _calc_geo_score(skill: Skill, requirements: dict) -> float:

    user_geo = requirements.get("geo")
    if not user_geo:
        return 100.0
    dist = _haversine_km(skill.geo, user_geo)
    radius = requirements.get("radius_km", 50.0)
    if radius <= 0:
        return 0.0
    score = max(0.0, 100.0 - (dist / radius) * 100.0)
    return round(score, 2)


def _calc_budget_match(skill: Skill, requirements: dict) -> float:
    budget = requirements.get("budget")
    if budget is None or budget <= 0:
        return 100.0
    if skill.price <= budget:
        return 100.0
    ratio = budget / skill.price
    return round(max(0.0, ratio * 100), 2)


def match_score(skill: Skill, requirements: dict) -> MatchResult:
    """40/30/20/10 加权评分：
    40% 技能匹配度
    30% 信誉评分
    20% 地理位置
    10% 预算匹配
    """
    skill_score = _calc_skill_match(skill, requirements)
    reputation_score = (skill.rating / 5.0) * 100.0
    geo_score = _calc_geo_score(skill, requirements)
    budget_score = _calc_budget_match(skill, requirements)

    total = skill_score * 0.4 + reputation_score * 0.3 + geo_score * 0.2 + budget_score * 0.1

    return MatchResult(
        skill=skill,
        score=round(total, 2),
        breakdown={
            "skill": skill_score,
            "reputation": reputation_score,
            "geo": geo_score,
            "budget": budget_score,
        },
    )


def find_best_matches(
    requirements: dict,
    skills_pool: list[Skill],
    top_n: int = 5,
) -> list[MatchResult]:
    """主入口：地理过滤 → 评分排序 → 返回 Top N。"""
    user_geo = requirements.get("geo")
    radius = requirements.get("radius_km", 50.0)

    if user_geo:
        candidates = [s for s in skills_pool if geo_filter(s, user_geo, radius)]
    else:
        candidates = list(skills_pool)

    scored = [match_score(s, requirements) for s in candidates]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_n]
