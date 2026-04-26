"""Tests for skill matcher engine."""

import pytest

from src.skills.matcher import (
    Skill,
    _haversine_km,
    find_best_matches,
    geo_filter,
    match_score,
)


def _make_skill(
    name: str = "test",
    category: str = "programming",
    lat: float = 22.5,
    lng: float = 114.1,
    price: float = 50.0,
    rating: float = 4.0,
    tags: list | None = None,
) -> Skill:
    return Skill(
        name=name,
        category=category,
        geo=(lat, lng),
        price=price,
        rating=rating,
        tags=tags or [],
    )


class TestHaversine:
    def test_zero_distance(self):
        p = (22.5, 114.1)
        assert _haversine_km(p, p) == 0.0

    def test_shenzhen_to_beijing(self):
        dist = _haversine_km((22.5, 114.1), (39.9, 116.4))
        assert 1900 < dist < 2000  # ~1950 km

    def test_known_distance(self):
        dist = _haversine_km((0.0, 0.0), (0.0, 1.0))
        assert 110 < dist < 112  # ~111 km


class TestGeoFilter:
    def test_within_radius(self):
        skill = _make_skill(lat=22.5, lng=114.1)
        assert geo_filter(skill, (22.55, 114.15), radius_km=50.0)

    def test_outside_radius(self):
        skill = _make_skill(lat=22.5, lng=114.1)
        assert not geo_filter(skill, (39.9, 116.4), radius_km=50.0)

    def test_edge_case(self):
        skill = _make_skill(lat=22.5, lng=114.1)
        assert geo_filter(skill, (22.5, 114.1), radius_km=0.0)


class TestMatchScore:
    def test_perfect_match(self):
        skills_pool = [_make_skill()]
        requirements = {
            "category": "programming",
            "geo": (22.5, 114.1),
            "radius_km": 50.0,
            "budget": 100.0,
            "tags": [],
        }
        result = match_score(skills_pool[0], requirements)
        assert result.score > 90.0
        assert result.breakdown["skill"] == 100.0

    def test_rating_impact(self):
        low_rating = _make_skill(rating=1.0)
        high_rating = _make_skill(rating=5.0)
        requirements = {"geo": (22.5, 114.1), "radius_km": 50.0}
        low_score = match_score(low_rating, requirements).score
        high_score = match_score(high_rating, requirements).score
        assert high_score > low_score

    def test_budget_under(self):
        skill = _make_skill(price=200.0)
        requirements = {"budget": 50.0, "geo": (22.5, 114.1)}
        result = match_score(skill, requirements)
        assert result.breakdown["budget"] < 100.0


class TestFindBestMatches:
    def test_top_n(self):
        pool = [_make_skill(name=f"s{i}", rating=float(i)) for i in range(10)]
        requirements = {"geo": (22.5, 114.1), "radius_km": 100.0}
        results = find_best_matches(requirements, pool, top_n=3)
        assert len(results) == 3

    def test_geo_exclusion(self):
        near = _make_skill(name="near", lat=22.5, lng=114.1)
        far = _make_skill(name="far", lat=39.9, lng=116.4)
        requirements = {"geo": (22.5, 114.1), "radius_km": 50.0}
        results = find_best_matches(requirements, [near, far])
        assert len(results) == 1
        assert results[0].skill.name == "near"

    def test_empty_pool(self):
        results = find_best_matches({"geo": (22.5, 114.1)}, [])
        assert results == []

    def test_sort_order(self):
        pool = [
            _make_skill(name="low", rating=1.0),
            _make_skill(name="high", rating=5.0),
        ]
        requirements = {"geo": (22.5, 114.1), "radius_km": 100.0}
        results = find_best_matches(requirements, pool, top_n=2)
        assert results[0].skill.name == "high"
        assert results[1].skill.name == "low"
