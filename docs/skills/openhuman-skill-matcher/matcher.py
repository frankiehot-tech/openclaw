#!/usr/bin/env python3
"""
OpenHuman Skill-Matcher v1.0
基于 OpenHuman 协议的技能匹配核心模块
权重: 40(技能) / 30(经验) / 20(地点) / 10(其他)
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SkillProfile:
    """技能画像"""

    skills: List[str]
    experience_years: float
    location: str
    availability: str
    hourly_rate: float


@dataclass
class JobRequirement:
    """职位需求"""

    required_skills: List[str]
    min_experience: float
    location: str
    budget: float


class SkillMatcher:
    """技能匹配器"""

    # 权重配置
    WEIGHT_SKILLS = 40
    WEIGHT_EXPERIENCE = 30
    WEIGHT_LOCATION = 20
    WEIGHT_OTHER = 10

    def __init__(self):
        self.match_history = []

    def calculate_similarity(self, skills1: List[str], skills2: List[str]) -> float:
        """计算技能相似度"""
        if not skills1 or not skills2:
            return 0.0

        set1, set2 = set(skills1), set(skills2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def calculate_location_score(self, profile_loc: str, job_loc: str) -> float:
        """计算地理位置匹配分数"""
        # 远程/可远程选项
        if (
            "远程" in profile_loc
            or "远程" in job_loc
            or "可远程" in profile_loc
            or "可远程" in job_loc
        ):
            return 1.0

        # 同一城市
        if profile_loc == job_loc:
            return 1.0

        # 同一区域（华东、华南、华北等）
        regions = {
            "华东": ["上海", "杭州", "苏州", "南京", "青岛"],
            "华南": ["深圳", "广州", "成都", "重庆"],
            "华北": ["北京", "天津"],
            "华中": ["武汉", "长沙", "郑州"],
            "西北": ["西安"],
        }

        for region, cities in regions.items():
            if profile_loc in cities and job_loc in cities:
                return 0.7  # 同区域高分

        # 同省份
        if profile_loc[:2] == job_loc[:2]:
            return 0.5

        return 0.2  # 降低到 0.2，保留基础分

    def match(self, profile: SkillProfile, requirement: JobRequirement) -> Dict:
        """执行匹配计算"""

        # 1. 技能匹配 (40%)
        skill_similarity = self.calculate_similarity(profile.skills, requirement.required_skills)
        skill_score = skill_similarity * self.WEIGHT_SKILLS

        # 2. 经验匹配 (30%)
        exp_ratio = min(profile.experience_years / requirement.min_experience, 1.5)
        exp_score = exp_ratio * self.WEIGHT_EXPERIENCE

        # 3. 地点匹配 (20%) - 硬门槛
        loc_score = (
            self.calculate_location_score(profile.location, requirement.location)
            * self.WEIGHT_LOCATION
        )

        # 4. 其他因素 (10%)
        other_score = self.WEIGHT_OTHER  # 基础分

        # 总分
        total_score = skill_score + exp_score + loc_score + other_score

        # 硬门槛检查
        location_pass = loc_score >= self.WEIGHT_LOCATION * 0.5

        return {
            "total_score": round(total_score, 2),
            "breakdown": {
                "skills": round(skill_score, 2),
                "experience": round(exp_score, 2),
                "location": round(loc_score, 2),
                "other": round(other_score, 2),
            },
            "location_pass": location_pass,
            "match_level": (
                "HIGH" if total_score >= 80 else "MEDIUM" if total_score >= 60 else "LOW"
            ),
        }


# 测试
if __name__ == "__main__":
    matcher = SkillMatcher()

    profile = SkillProfile(
        skills=["Python", "React", "PostgreSQL", "AWS"],
        experience_years=5,
        location="上海",
        availability="随时",
        hourly_rate=150,
    )

    requirement = JobRequirement(
        required_skills=["Python", "React", "AWS"], min_experience=3, location="上海", budget=200
    )

    result = matcher.match(profile, requirement)
    print(f"匹配结果: {result}")
