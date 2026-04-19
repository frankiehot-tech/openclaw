#!/usr/bin/env python3
"""
GitHub工作流评估框架
基于代码质量而非Star数量评估项目，为Clawra模块补强选择最佳集成候选
"""

import json
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class GitHubProjectEvaluator:
    """GitHub项目评估器"""

    def __init__(self):
        self.categories = {
            "video_generation": [
                "视频生成",
                "视频处理",
                "ffmpeg",
                "moviepy",
                "OpenCV",
                "video pipeline",
                "video editing",
                "video automation",
            ],
            "ai_content_generation": [
                "stable diffusion",
                "DALL-E",
                "Midjourney",
                "文生图",
                "图生视频",
                "AI video",
                "AI image generation",
                "prompt engineering",
            ],
            "media_asset_management": [
                "媒体管理",
                "元数据",
                "资产管理",
                "版本控制",
                "批量处理",
                "media library",
                "asset management",
                "metadata",
            ],
        }

        # 评估权重（总计100%）
        self.weights = {
            "code_quality": 0.30,  # 代码质量
            "maintenance": 0.25,  # 维护状态
            "integration_friendly": 0.20,  # 集成友好性
            "function_value": 0.15,  # 功能价值
            "community": 0.10,  # 社区生态
        }

    def search_github(self, query: str, category: str, limit: int = 20) -> List[Dict]:
        """使用gh命令搜索GitHub项目"""
        print(f"搜索类别 '{category}': {query}")

        # 构建搜索查询 - 限制语言和主题
        search_query = f"{query} language:python topic:video topic:ai topic:automation"

        try:
            # 使用gh搜索
            cmd = [
                "gh",
                "search",
                "repos",
                search_query,
                "--limit",
                str(limit),
                "--json",
                "name,fullName,description,stargazersCount,updatedAt,language",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            repos = json.loads(result.stdout)
            print(f"找到 {len(repos)} 个仓库")

            # 添加分类信息
            for repo in repos:
                repo["category"] = category
                repo["search_query"] = query

            return repos

        except subprocess.CalledProcessError as e:
            print(f"GitHub搜索失败: {e}")
            print(f"错误输出: {e.stderr}")
            return []
        except FileNotFoundError:
            print("未安装gh命令行工具，请先安装: https://cli.github.com/")
            return []

    def evaluate_code_quality(self, repo: Dict) -> float:
        """评估代码质量"""
        score = 0.0

        try:
            # 克隆仓库（浅克隆）
            repo_url = f"https://github.com/{repo['fullName']}.git"
            clone_dir = f"/tmp/github_eval_{repo['fullName'].replace('/', '_')}"

            if os.path.exists(clone_dir):
                subprocess.run(["rm", "-rf", clone_dir], check=True)

            # 浅克隆
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, clone_dir],
                capture_output=True,
                check=True,
                timeout=300,
            )

            # 评估指标
            metrics = self._analyze_codebase(clone_dir)

            # 计算代码质量分数
            # 1. 代码结构（目录组织）
            if metrics["has_clear_structure"]:
                score += 0.2

            # 2. 文档完整性
            score += metrics["doc_coverage"] * 0.2

            # 3. 测试覆盖率
            score += metrics["test_coverage"] * 0.3

            # 4. 代码规范性
            score += metrics["code_standards"] * 0.3

            # 清理
            subprocess.run(["rm", "-rf", clone_dir], check=False)

        except Exception as e:
            print(f"评估代码质量失败 {repo['fullName']}: {e}")
            score = 0.3  # 基础分

        return min(score, 1.0)

    def _analyze_codebase(self, clone_dir: str) -> Dict:
        """分析代码库"""
        metrics = {
            "has_clear_structure": False,
            "doc_coverage": 0.0,
            "test_coverage": 0.0,
            "code_standards": 0.0,
        }

        try:
            # 检查目录结构
            dirs = ["src", "lib", "app", "tests", "docs", "examples"]
            dir_count = sum(1 for d in dirs if os.path.exists(os.path.join(clone_dir, d)))
            metrics["has_clear_structure"] = dir_count >= 3

            # 检查文档
            doc_files = ["README.md", "README.rst", "README.txt", "docs/", "CONTRIBUTING.md"]
            doc_count = sum(1 for f in doc_files if os.path.exists(os.path.join(clone_dir, f)))
            metrics["doc_coverage"] = min(doc_count / 3, 1.0)

            # 检查测试
            test_files = []
            for root, dirs, files in os.walk(clone_dir):
                if "test" in root.lower() or "tests" in root:
                    test_files.extend([os.path.join(root, f) for f in files if f.endswith(".py")])

            total_py_files = sum(
                1 for root, dirs, files in os.walk(clone_dir) for f in files if f.endswith(".py")
            )

            if total_py_files > 0:
                metrics["test_coverage"] = min(len(test_files) / total_py_files * 2, 1.0)

            # 检查代码规范（简单检查）
            # 检查是否有配置文件：.pylintrc, .flake8, pyproject.toml, setup.cfg
            config_files = [
                ".pylintrc",
                ".flake8",
                "pyproject.toml",
                "setup.cfg",
                ".pre-commit-config.yaml",
            ]
            config_count = sum(
                1 for f in config_files if os.path.exists(os.path.join(clone_dir, f))
            )
            metrics["code_standards"] = min(config_count / 2, 1.0)

        except Exception as e:
            print(f"分析代码库失败: {e}")

        return metrics

    def evaluate_maintenance(self, repo: Dict) -> float:
        """评估维护状态"""
        score = 0.0

        try:
            # 解析更新时间
            updated_at = datetime.fromisoformat(repo["updatedAt"].replace("Z", "+00:00"))
            now = datetime.now(updated_at.tzinfo)
            days_since_update = (now - updated_at).days

            # 1. 最近更新（0-30天：1.0，31-90天：0.7，91-180天：0.4，181+天：0.1）
            if days_since_update <= 30:
                score += 0.4
            elif days_since_update <= 90:
                score += 0.28
            elif days_since_update <= 180:
                score += 0.16
            else:
                score += 0.04

            # 2. 获取更多维护信息（issues, releases）
            try:
                # 使用gh获取issues和releases计数
                issues_cmd = ["gh", "api", f'/repos/{repo["fullName"]}', "-q", ".open_issues_count"]
                issues_result = subprocess.run(
                    issues_cmd, capture_output=True, text=True, check=True
                )
                open_issues = int(issues_result.stdout.strip())

                # 问题响应率（假设）
                if open_issues > 0:
                    # 简单假设：问题越少，维护越好
                    issue_score = 1.0 / (1 + open_issues / 10)
                    score += issue_score * 0.3
                else:
                    score += 0.3

            except:
                score += 0.15  # 基础分

            # 3. 版本发布
            try:
                releases_cmd = [
                    "gh",
                    "api",
                    f'/repos/{repo["fullName"]}/releases',
                    "--paginate",
                    "-q",
                    "length",
                ]
                releases_result = subprocess.run(
                    releases_cmd, capture_output=True, text=True, check=True
                )
                release_count = int(releases_result.stdout.strip())

                if release_count >= 5:
                    score += 0.3
                elif release_count >= 2:
                    score += 0.2
                else:
                    score += 0.1
            except:
                score += 0.1  # 基础分

        except Exception as e:
            print(f"评估维护状态失败 {repo['fullName']}: {e}")
            score = 0.3  # 基础分

        return min(score, 1.0)

    def evaluate_integration_friendly(self, repo: Dict) -> float:
        """评估集成友好性"""
        score = 0.0

        try:
            # 1. API设计
            # 检查是否有清晰的API文档或模块结构
            repo_url = f"https://github.com/{repo['fullName']}"

            # 检查描述中是否有API相关关键词
            desc = repo.get("description", "").lower()
            api_keywords = ["api", "library", "sdk", "client", "wrapper", "interface"]
            has_api_keyword = any(kw in desc for kw in api_keywords)

            if has_api_keyword:
                score += 0.3

            # 2. 依赖管理
            # 检查是否有requirements.txt, setup.py, pyproject.toml
            try:
                # 浅克隆检查依赖文件
                clone_dir = f"/tmp/github_integ_{repo['fullName'].replace('/', '_')}"

                if not os.path.exists(clone_dir):
                    subprocess.run(
                        ["git", "clone", "--depth", "1", repo_url, clone_dir],
                        capture_output=True,
                        timeout=120,
                        check=True,
                    )

                dep_files = [
                    "requirements.txt",
                    "setup.py",
                    "pyproject.toml",
                    "Pipfile",
                    "environment.yml",
                ]
                dep_count = sum(1 for f in dep_files if os.path.exists(os.path.join(clone_dir, f)))

                if dep_count >= 1:
                    score += 0.3
                else:
                    score += 0.1

                # 检查依赖复杂性
                if os.path.exists(os.path.join(clone_dir, "requirements.txt")):
                    with open(os.path.join(clone_dir, "requirements.txt"), "r") as f:
                        deps = f.readlines()
                    simple_deps = len(
                        [d for d in deps if not d.strip().startswith("#") and d.strip()]
                    )
                    if simple_deps <= 10:
                        score += 0.2
                    else:
                        score += 0.1
                else:
                    score += 0.1

                # 清理
                subprocess.run(["rm", "-rf", clone_dir], check=False)

            except:
                score += 0.2  # 基础分

            # 3. 文档质量
            # 检查README是否详细
            if "documentation" in desc or "docs" in desc or "example" in desc:
                score += 0.2
            else:
                score += 0.1

        except Exception as e:
            print(f"评估集成友好性失败 {repo['fullName']}: {e}")
            score = 0.3  # 基础分

        return min(score, 1.0)

    def evaluate_function_value(self, repo: Dict, category: str) -> float:
        """评估功能价值"""
        score = 0.0

        try:
            desc = repo.get("description", "").lower()
            name = repo.get("name", "").lower()

            # 根据类别评估功能价值
            if category == "video_generation":
                video_keywords = [
                    "video",
                    "ffmpeg",
                    "moviepy",
                    "opencv",
                    "editing",
                    "processing",
                    "pipeline",
                ]
                keyword_matches = sum(1 for kw in video_keywords if kw in desc or kw in name)
                score = min(keyword_matches / 3, 1.0) * 0.5

                # 检查是否解决实际问题
                problem_keywords = ["automate", "workflow", "batch", "convert", "process"]
                if any(kw in desc for kw in problem_keywords):
                    score += 0.3
                else:
                    score += 0.15

            elif category == "ai_content_generation":
                ai_keywords = [
                    "ai",
                    "stable diffusion",
                    "dall-e",
                    "midjourney",
                    "generation",
                    "prompt",
                ]
                keyword_matches = sum(1 for kw in ai_keywords if kw in desc or kw in name)
                score = min(keyword_matches / 3, 1.0) * 0.5

                # 检查是否提供完整工作流
                if "workflow" in desc or "pipeline" in desc:
                    score += 0.3
                else:
                    score += 0.15

            elif category == "media_asset_management":
                media_keywords = ["media", "asset", "management", "metadata", "library", "organize"]
                keyword_matches = sum(1 for kw in media_keywords if kw in desc or kw in name)
                score = min(keyword_matches / 3, 1.0) * 0.5

                # 检查是否支持批量操作
                if "batch" in desc or "bulk" in desc:
                    score += 0.3
                else:
                    score += 0.15

            # 额外加分：明确解决Clawra相关问题的
            clawra_keywords = ["content generation", "automation", "workflow", "integration"]
            if any(kw in desc for kw in clawra_keywords):
                score += 0.2

        except Exception as e:
            print(f"评估功能价值失败 {repo['fullName']}: {e}")
            score = 0.3  # 基础分

        return min(score, 1.0)

    def evaluate_community(self, repo: Dict) -> float:
        """评估社区生态"""
        score = 0.0

        try:
            # 1. Star数量（对数尺度）
            stars = repo.get("stargazersCount", 0)
            if stars > 1000:
                score += 0.4
            elif stars > 100:
                score += 0.3
            elif stars > 10:
                score += 0.2
            else:
                score += 0.1

            # 2. 贡献者数量（通过API获取）
            try:
                contrib_cmd = [
                    "gh",
                    "api",
                    f'/repos/{repo["fullName"]}/contributors',
                    "-q",
                    "length",
                ]
                contrib_result = subprocess.run(
                    contrib_cmd, capture_output=True, text=True, check=True
                )
                contributors = int(contrib_result.stdout.strip())

                if contributors > 5:
                    score += 0.3
                elif contributors > 1:
                    score += 0.2
                else:
                    score += 0.1
            except:
                score += 0.1  # 基础分

            # 3. 生态系统（检查相关项目）
            try:
                # 检查是否有相关主题
                topics_cmd = ["gh", "api", f'/repos/{repo["fullName"]}', "-q", ".topics"]
                topics_result = subprocess.run(
                    topics_cmd, capture_output=True, text=True, check=True
                )
                topics = json.loads(topics_result.stdout)

                if len(topics) >= 3:
                    score += 0.3
                elif len(topics) >= 1:
                    score += 0.2
                else:
                    score += 0.1
            except:
                score += 0.1  # 基础分

        except Exception as e:
            print(f"评估社区生态失败 {repo['fullName']}: {e}")
            score = 0.3  # 基础分

        return min(score, 1.0)

    def evaluate_project(self, repo: Dict) -> Dict:
        """完整评估项目"""
        print(f"评估项目: {repo['fullName']}")

        category = repo.get("category", "unknown")

        # 各项评估
        code_quality_score = self.evaluate_code_quality(repo)
        maintenance_score = self.evaluate_maintenance(repo)
        integration_score = self.evaluate_integration_friendly(repo)
        function_score = self.evaluate_function_value(repo, category)
        community_score = self.evaluate_community(repo)

        # 加权总分
        total_score = (
            code_quality_score * self.weights["code_quality"]
            + maintenance_score * self.weights["maintenance"]
            + integration_score * self.weights["integration_friendly"]
            + function_score * self.weights["function_value"]
            + community_score * self.weights["community"]
        )

        # 评级
        if total_score >= 0.8:
            rating = "A"
        elif total_score >= 0.7:
            rating = "B"
        elif total_score >= 0.6:
            rating = "C"
        elif total_score >= 0.5:
            rating = "D"
        else:
            rating = "F"

        evaluation = {
            "full_name": repo["fullName"],
            "description": repo.get("description", ""),
            "stars": repo.get("stargazersCount", 0),
            "updated_at": repo.get("updatedAt", ""),
            "category": category,
            "scores": {
                "code_quality": code_quality_score,
                "maintenance": maintenance_score,
                "integration_friendly": integration_score,
                "function_value": function_score,
                "community": community_score,
                "total": total_score,
            },
            "rating": rating,
            "url": f"https://github.com/{repo['fullName']}",
        }

        print(f"  评分: {rating} ({total_score:.2f})")

        return evaluation

    def search_and_evaluate(self, max_per_category: int = 10) -> List[Dict]:
        """搜索并评估项目"""
        all_repos = []
        evaluations = []

        # 搜索每个类别
        for category, queries in self.categories.items():
            print(f"\n{'='*60}")
            print(f"搜索类别: {category}")
            print(f"{'='*60}")

            for query in queries[:2]:  # 每个类别只搜索前2个查询
                repos = self.search_github(query, category, limit=max_per_category // 2)
                all_repos.extend(repos)

                # 避免重复
                seen = set()
                unique_repos = []
                for repo in repos:
                    if repo["fullName"] not in seen:
                        seen.add(repo["fullName"])
                        unique_repos.append(repo)

                # 评估项目
                for repo in unique_repos[:3]:  # 每个查询只评估前3个
                    evaluation = self.evaluate_project(repo)
                    evaluations.append(evaluation)

        # 按总分排序
        evaluations.sort(key=lambda x: x["scores"]["total"], reverse=True)

        return evaluations


def generate_report(
    evaluations: List[Dict], output_file: str = "github_workflow_evaluation_report.json"
):
    """生成评估报告"""

    # 按类别分组
    by_category = {}
    for eval in evaluations:
        category = eval["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(eval)

    # 统计信息
    stats = {
        "total_evaluated": len(evaluations),
        "by_category": {cat: len(evals) for cat, evals in by_category.items()},
        "rating_distribution": {
            "A": len([e for e in evaluations if e["rating"] == "A"]),
            "B": len([e for e in evaluations if e["rating"] == "B"]),
            "C": len([e for e in evaluations if e["rating"] == "C"]),
            "D": len([e for e in evaluations if e["rating"] == "D"]),
            "F": len([e for e in evaluations if e["rating"] == "F"]),
        },
        "top_projects": evaluations[:10],
    }

    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "evaluations": evaluations,
        "recommendations": [],
    }

    # 生成推荐
    for category, evals in by_category.items():
        top_in_category = sorted(evals, key=lambda x: x["scores"]["total"], reverse=True)[:3]
        if top_in_category:
            report["recommendations"].append(
                {
                    "category": category,
                    "top_projects": [
                        {
                            "name": e["full_name"],
                            "score": e["scores"]["total"],
                            "rating": e["rating"],
                            "url": e["url"],
                            "reason": f"代码质量: {e['scores']['code_quality']:.2f}, 维护状态: {e['scores']['maintenance']:.2f}",
                        }
                        for e in top_in_category
                    ],
                }
            )

    # 保存报告
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n评估报告已保存到: {output_file}")

    # 打印摘要
    print(f"\n{'='*60}")
    print("GitHub工作流评估摘要")
    print(f"{'='*60}")
    print(f"评估项目总数: {stats['total_evaluated']}")
    print(f"按类别分布: {stats['by_category']}")
    print(f"评级分布: {stats['rating_distribution']}")

    print(f"\n📊 推荐集成项目（前10）:")
    for i, project in enumerate(stats["top_projects"][:10], 1):
        print(
            f"{i:2d}. [{project['rating']}] {project['full_name']} (总分: {project['scores']['total']:.2f})"
        )
        print(f"     {project['description'][:80]}...")

    return report


def main():
    """主函数"""
    print("GitHub工作流评估框架")
    print("=" * 60)
    print("基于代码质量而非Star数量的项目评估")
    print("=" * 60)

    evaluator = GitHubProjectEvaluator()

    # 搜索和评估
    print("\n开始搜索和评估GitHub项目...")
    evaluations = evaluator.search_and_evaluate(max_per_category=5)

    if not evaluations:
        print("未找到可评估的项目")
        return

    # 生成报告
    report = generate_report(evaluations)

    print(f"\n✅ 评估完成")
    print(f"\n🎯 下一步行动:")
    print("1. 审查评估报告中的推荐项目")
    print("2. 对A级项目进行深度技术评估")
    print("3. 设计集成方案（适配器模式）")
    print("4. 进行试点集成和测试")
    print("5. 基于测试结果决定全面集成")


if __name__ == "__main__":
    main()
