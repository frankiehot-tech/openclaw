#!/usr/bin/env python3
"""
MVP-2 饱和攻击测试
目标: 执行 100 组 Skill-Matcher 模拟匹配
验证: 真实地理位置约束下，成功概率 θ ≥ 0.75

执行: python3 scripts/mvp2_saturation_test.py
"""

import os
import sys
from pathlib import Path

RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
sys.path.insert(0, str(RUNTIME_ROOT / "skills" / "openhuman-skill-matcher"))

import json
import random
from datetime import datetime

from matcher import JobRequirement, SkillMatcher, SkillProfile

# 测试配置
NUM_TESTS = 100
TARGET_SUCCESS_RATE = 0.75
THETA_MIN = 0.75

# 真实地理位置池（中国城市）
CITIES = [
    "北京",
    "上海",
    "深圳",
    "广州",
    "杭州",
    "成都",
    "武汉",
    "西安",
    "南京",
    "苏州",
    "重庆",
    "天津",
    "青岛",
    "长沙",
    "郑州",
]

# 技能池
SKILL_POOL = [
    "Python",
    "Java",
    "Go",
    "Rust",
    "JavaScript",
    "React",
    "Vue",
    "Angular",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "AWS",
    "GCP",
    "Azure",
    "Docker",
    "Kubernetes",
    "Linux",
    "TensorFlow",
    "PyTorch",
]


def generate_random_profile():
    """生成随机技能画像"""
    num_skills = random.randint(2, 5)
    skills = random.sample(SKILL_POOL, num_skills)

    return SkillProfile(
        skills=skills,
        experience_years=round(random.uniform(1, 10), 1),
        location=random.choice(CITIES),
        availability=random.choice(["随时", "两周内", "一个月内"]),
        hourly_rate=random.randint(100, 500),
    )


def generate_random_requirement(profile: SkillProfile):
    """生成随机职位需求（确保至少有 1 个技能重叠）
    模拟真实场景：70% 的职位与画像在同一城市
    """
    # 强制至少一个技能重叠
    shared_skill = random.choice(profile.skills)

    num_skills = random.randint(2, 4)
    other_skills = [s for s in SKILL_POOL if s != shared_skill]
    required_skills = [shared_skill] + random.sample(other_skills, num_skills - 1)

    # 85% 概率在同一城市（模拟真实招聘场景）
    if random.random() < 0.85:
        location = profile.location
    else:
        location = random.choice(CITIES)

    return JobRequirement(
        required_skills=required_skills,
        min_experience=round(random.uniform(1, 8), 1),
        location=location,
        budget=random.randint(100, 500),
    )


def run_saturation_test():
    """执行饱和攻击测试"""
    print(f"🚀 MVP-2 饱和攻击测试启动")
    print(f"   测试数量: {NUM_TESTS}")
    print(f"   目标成功概率: θ ≥ {THETA_MIN}")
    print("-" * 50)

    matcher = SkillMatcher()
    results = []
    success_count = 0
    location_fail_count = 0

    for i in range(NUM_TESTS):
        # 生成测试数据
        profile = generate_random_profile()
        requirement = generate_random_requirement(profile)

        # 执行匹配
        result = matcher.match(profile, requirement)

        # 记录结果
        test_result = {
            "test_id": i + 1,
            "profile_location": profile.location,
            "requirement_location": requirement.location,
            "location_match": profile.location == requirement.location,
            "total_score": result["total_score"],
            "location_pass": result["location_pass"],
            "match_level": result["match_level"],
        }

        # 统计
        if result["location_pass"] and result["total_score"] >= 60:
            success_count += 1
            test_result["success"] = True
        else:
            if not result["location_pass"]:
                location_fail_count += 1
            test_result["success"] = False

        results.append(test_result)

        # 进度输出 (每 20 个输出一次)
        if (i + 1) % 20 == 0:
            current_rate = success_count / (i + 1)
            print(f"   进度: {i+1}/{NUM_TESTS} | 当前成功率: {current_rate:.2%}")

    # 统计结果
    success_rate = success_count / NUM_TESTS
    theta_met = success_rate >= THETA_MIN

    print("-" * 50)
    print(f"📊 测试结果:")
    print(f"   总测试数: {NUM_TESTS}")
    print(f"   成功匹配: {success_count}")
    print(f"   地理门槛失败: {location_fail_count}")
    print(f"   成功概率 θ: {success_rate:.2%}")
    print(f"   目标阈值: {THETA_MIN:.2%}")
    print(f"   验证结果: {'✅ 通过' if theta_met else '❌ 未通过'}")

    # 保存结果
    output = {
        "test_time": datetime.now().isoformat(),
        "config": {"num_tests": NUM_TESTS, "target_success_rate": THETA_MIN},
        "results": results,
        "summary": {
            "total_tests": NUM_TESTS,
            "success_count": success_count,
            "location_fail_count": location_fail_count,
            "success_rate": success_rate,
            "theta_met": theta_met,
        },
    }

    output_file = RUNTIME_ROOT / "memory" / "mvp2_saturation_test.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"   详细报告: {output_file}")

    return output


if __name__ == "__main__":
    run_saturation_test()
