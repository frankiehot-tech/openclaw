#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP形象用户反馈系统
收集、分析用户对IP形象的反馈，并生成优化建议

功能：
1. 收集用户反馈（评分、评论、建议）
2. 存储和管理反馈数据
3. 分析反馈趋势和关键问题
4. 生成优化建议报告
5. 与IP数字资产管理器集成

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import logging
import sqlite3
import statistics
import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""

    IP_IMAGE = "ip_image"  # IP形象反馈
    VISUAL_STYLE = "visual_style"  # 视觉风格反馈
    CONTENT_TEMPLATE = "content_template"  # 内容模板反馈
    BRAND_CONSISTENCY = "brand_consistency"  # 品牌一致性反馈
    OVERALL_EXPERIENCE = "overall_experience"  # 整体体验反馈


class FeedbackSource(Enum):
    """反馈来源"""

    GITHUB = "github"  # GitHub用户
    COMMUNITY = "community"  # 社区成员
    INTERNAL_TEAM = "internal_team"  # 内部团队
    EXTERNAL_USER = "external_user"  # 外部用户
    AUTOMATED_ANALYSIS = "automated_analysis"  # 自动分析


@dataclass
class FeedbackEntry:
    """反馈条目"""

    feedback_id: str
    feedback_type: FeedbackType
    source: FeedbackSource
    user_id: Optional[str]  # 用户ID（匿名化）
    timestamp: datetime

    # 评分（1-5分）
    rating: Optional[int] = None  # 1-5分，None表示未评分

    # 文本反馈
    comment: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackAnalysis:
    """反馈分析结果"""

    feedback_type: FeedbackType
    period_start: datetime
    period_end: datetime

    # 统计信息
    total_feedbacks: int
    average_rating: Optional[float]
    rating_distribution: Dict[int, int]  # 评分分布

    # 文本分析
    common_themes: List[Dict[str, Any]]  # 常见主题
    sentiment_score: Optional[float]  # 情感分析得分（-1到1）

    # 关键词
    top_keywords: List[Dict[str, Any]]

    # 建议和问题
    improvement_suggestions: List[str]
    critical_issues: List[str]

    # 趋势分析
    trend: str  # improving, declining, stable


class IPFeedbackSystem:
    """IP形象反馈系统"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化反馈系统

        Args:
            db_path: SQLite数据库路径，默认为当前目录下的feedback.db
        """
        if db_path is None:
            self.db_path = Path(__file__).parent / "data" / "ip_feedback.db"
        else:
            self.db_path = Path(db_path)

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化锁（用于数据库写入同步）
        self._lock = threading.Lock()

        # 初始化数据库
        self._init_database()

        logger.info(f"IP反馈系统初始化完成，数据库: {self.db_path}")

    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建反馈表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id TEXT PRIMARY KEY,
            feedback_type TEXT NOT NULL,
            source TEXT NOT NULL,
            user_id TEXT,
            timestamp DATETIME NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            suggestions_json TEXT,
            context_json TEXT,
            metadata_json TEXT
        )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON feedback(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rating ON feedback(rating)")

        conn.commit()
        conn.close()

    def submit_feedback(self, feedback: FeedbackEntry, max_retries: int = 5) -> bool:
        """
        提交用户反馈，带有重试逻辑和锁同步

        Args:
            feedback: 反馈条目
            max_retries: 最大重试次数（默认5次）

        Returns:
            是否成功提交
        """
        import time

        # 使用锁确保同一时间只有一个写入操作
        with self._lock:
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                    INSERT INTO feedback
                    (feedback_id, feedback_type, source, user_id, timestamp, rating, comment, suggestions_json, context_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            feedback.feedback_id,
                            feedback.feedback_type.value,
                            feedback.source.value,
                            feedback.user_id,
                            feedback.timestamp.isoformat(),
                            feedback.rating,
                            feedback.comment,
                            json.dumps(feedback.suggestions, ensure_ascii=False),
                            json.dumps(feedback.context, ensure_ascii=False),
                            json.dumps(feedback.metadata, ensure_ascii=False),
                        ),
                    )

                    conn.commit()
                    conn.close()

                    logger.info(f"反馈提交成功: {feedback.feedback_id}")
                    return True

                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < max_retries - 1:
                        # 指数退避等待：0.5s, 1s, 2s, 4s, 8s
                        wait_time = 0.5 * (2**attempt)
                        logger.warning(
                            f"数据库锁定，重试 {attempt + 1}/{max_retries} (等待 {wait_time:.1f}s)"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"反馈提交失败（数据库锁定）: {e}")
                        return False
                except sqlite3.IntegrityError as e:
                    # UNIQUE constraint failed 错误
                    logger.error(f"反馈提交失败（唯一性约束）: {e}")
                    return False
                except Exception as e:
                    logger.error(f"反馈提交失败: {e}")
                    return False

            return False

    def collect_github_feedback(
        self, issue_data: Dict[str, Any], feedback_type: FeedbackType = FeedbackType.IP_IMAGE
    ) -> bool:
        """
        从GitHub Issue收集反馈

        Args:
            issue_data: GitHub Issue数据
            feedback_type: 反馈类型

        Returns:
            是否成功收集
        """
        try:
            # 从GitHub Issue提取反馈信息
            feedback_id = f"github_{issue_data.get('id', 'unknown')}"

            # 尝试从Issue内容提取评分
            rating = None
            comment = issue_data.get("body", "")

            # 简单的情感分析（简化版）
            sentiment_keywords = {
                "positive": ["好", "优秀", "很棒", "喜欢", "赞", "awesome", "great", "love"],
                "negative": ["差", "糟糕", "不好", "问题", "bug", "issue", "不好用", "poor"],
            }

            # 提取评分（如果Issue中有1-5分的评分）
            import re

            rating_match = re.search(r"评分[：:]\s*(\d)", comment)
            if rating_match:
                rating = int(rating_match.group(1))
            else:
                # 基于关键词的情感分析
                positive_count = sum(
                    1 for word in sentiment_keywords["positive"] if word in comment.lower()
                )
                negative_count = sum(
                    1 for word in sentiment_keywords["negative"] if word in comment.lower()
                )

                if positive_count > negative_count:
                    rating = 4  # 积极反馈
                elif negative_count > positive_count:
                    rating = 2  # 消极反馈
                else:
                    rating = 3  # 中性反馈

            # 提取建议
            suggestions = []
            suggestion_patterns = [
                r"建议[：:]\s*(.*?)(?:\n|$)",
                r"建议[：:]\s*([^。！？!?]+[。！？!?])",
                r"应该\s*(.*?)[。！？!?]",
            ]

            for pattern in suggestion_patterns:
                matches = re.findall(pattern, comment)
                suggestions.extend(matches)

            # 创建反馈条目
            feedback = FeedbackEntry(
                feedback_id=feedback_id,
                feedback_type=feedback_type,
                source=FeedbackSource.GITHUB,
                user_id=issue_data.get("user", {}).get("login", "anonymous"),
                timestamp=datetime.fromisoformat(
                    issue_data.get("created_at", datetime.now().isoformat()).replace("Z", "")
                ),
                rating=rating,
                comment=comment,
                suggestions=suggestions[:5],  # 最多5条建议
                context={
                    "issue_url": issue_data.get("html_url"),
                    "issue_title": issue_data.get("title"),
                    "issue_state": issue_data.get("state"),
                    "labels": issue_data.get("labels", []),
                },
                metadata={
                    "collection_method": "github_issue",
                    "collection_timestamp": datetime.now().isoformat(),
                },
            )

            return self.submit_feedback(feedback)

        except Exception as e:
            logger.error(f"GitHub反馈收集失败: {e}")
            return False

    def collect_user_survey_feedback(
        self, survey_data: Dict[str, Any], source: FeedbackSource = FeedbackSource.EXTERNAL_USER
    ) -> bool:
        """
        收集用户调查反馈

        Args:
            survey_data: 调查数据
            source: 反馈来源

        Returns:
            是否成功收集
        """
        try:
            feedback_id = f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(survey_data)) % 10000:04d}"

            feedback = FeedbackEntry(
                feedback_id=feedback_id,
                feedback_type=FeedbackType(survey_data.get("feedback_type", "ip_image")),
                source=source,
                user_id=survey_data.get("user_id", "anonymous"),
                timestamp=datetime.now(),
                rating=survey_data.get("rating"),
                comment=survey_data.get("comment"),
                suggestions=survey_data.get("suggestions", []),
                context={
                    "survey_id": survey_data.get("survey_id"),
                    "survey_version": survey_data.get("version", "1.0"),
                    "questions": survey_data.get("questions", []),
                },
                metadata={
                    "collection_method": "user_survey",
                    "survey_type": survey_data.get("survey_type", "general"),
                },
            )

            return self.submit_feedback(feedback)

        except Exception as e:
            logger.error(f"用户调查反馈收集失败: {e}")
            return False

    def get_feedback_statistics(self) -> Dict[str, Any]:
        """
        获取反馈统计数据

        Returns:
            包含统计数据的字典
        """
        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取总反馈数
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total_feedbacks = cursor.fetchone()[0]

            # 获取各类型反馈数
            cursor.execute("SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type")
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 获取平均评分
            cursor.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL")
            avg_rating_row = cursor.fetchone()
            average_rating = float(avg_rating_row[0]) if avg_rating_row[0] is not None else None

            # 获取最近反馈时间
            cursor.execute("SELECT MAX(timestamp) FROM feedback")
            latest_feedback = cursor.fetchone()[0]

            conn.close()

            return {
                "total_feedbacks": total_feedbacks,
                "average_rating": average_rating,
                "feedback_type_distribution": type_counts,
                "latest_feedback": latest_feedback,
                "database_path": self.db_path,
            }

        except Exception as e:
            logger.error(f"获取反馈统计失败: {e}")
            return {
                "total_feedbacks": 0,
                "average_rating": None,
                "feedback_type_distribution": {},
                "latest_feedback": None,
                "database_path": self.db_path,
                "error": str(e),
            }

    def analyze_feedback(
        self, feedback_type: Optional[FeedbackType] = None, days: int = 30
    ) -> Optional[FeedbackAnalysis]:
        """
        分析反馈数据

        Args:
            feedback_type: 反馈类型，None表示所有类型
            days: 分析最近多少天的数据

        Returns:
            反馈分析结果，如果无数据则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            # 时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            conditions.append("timestamp >= ?")
            conditions.append("timestamp <= ?")
            params.extend([start_date.isoformat(), end_date.isoformat()])

            # 反馈类型
            if feedback_type:
                conditions.append("feedback_type = ?")
                params.append(feedback_type.value)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询反馈数据
            query = f"""
            SELECT feedback_type, rating, comment, suggestions_json, timestamp
            FROM feedback
            WHERE {where_clause}
            ORDER BY timestamp DESC
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                logger.warning(
                    f"没有找到{feedback_type.value if feedback_type else '任何'}反馈数据"
                )
                return None

            # 提取数据
            ratings = []
            comments = []
            all_suggestions = []

            for row in rows:
                rating = row[1]
                comment = row[2]
                suggestions_json = row[3]

                if rating is not None:
                    ratings.append(rating)

                if comment:
                    comments.append(comment)

                if suggestions_json:
                    try:
                        suggestions = json.loads(suggestions_json)
                        all_suggestions.extend(suggestions)
                    except:
                        pass

            # 计算统计信息
            average_rating = statistics.mean(ratings) if ratings else None
            rating_distribution = dict(Counter(ratings))

            # 文本分析（简化版）
            common_themes = self._analyze_common_themes(comments)
            sentiment_score = self._analyze_sentiment(comments)
            top_keywords = self._extract_keywords(comments + all_suggestions)

            # 提取改进建议和关键问题
            improvement_suggestions = self._extract_improvement_suggestions(
                all_suggestions, comments
            )
            critical_issues = self._identify_critical_issues(comments)

            # 趋势分析（简化版）
            trend = self._analyze_trend(rows, days)

            # 创建分析结果
            analysis = FeedbackAnalysis(
                feedback_type=feedback_type or FeedbackType.IP_IMAGE,
                period_start=start_date,
                period_end=end_date,
                total_feedbacks=len(rows),
                average_rating=average_rating,
                rating_distribution=rating_distribution,
                common_themes=common_themes,
                sentiment_score=sentiment_score,
                top_keywords=top_keywords,
                improvement_suggestions=improvement_suggestions,
                critical_issues=critical_issues,
                trend=trend,
            )

            return analysis

        except Exception as e:
            logger.error(f"反馈分析失败: {e}")
            return None

    def _analyze_common_themes(self, comments: List[str]) -> List[Dict[str, Any]]:
        """分析常见主题（简化版）"""
        themes = []

        # 定义主题关键词
        theme_keywords = {
            "视觉设计": ["设计", "视觉", "颜色", "风格", "UI", "美观", "布局"],
            "内容质量": ["内容", "质量", "准确", "有用", "价值", "信息"],
            "用户体验": ["体验", "易用", "方便", "流畅", "交互", "界面"],
            "技术实现": ["技术", "性能", "速度", "稳定", "bug", "错误", "问题"],
            "品牌一致性": ["品牌", "一致", "形象", "识别", "调性", "风格"],
        }

        for theme, keywords in theme_keywords.items():
            count = 0
            matching_comments = []

            for comment in comments:
                if any(keyword in comment for keyword in keywords):
                    count += 1
                    matching_comments.append(
                        comment[:100] + "..." if len(comment) > 100 else comment
                    )

            if count > 0:
                themes.append(
                    {
                        "theme": theme,
                        "count": count,
                        "percentage": round(count / len(comments) * 100, 1) if comments else 0,
                        "sample_comments": matching_comments[:3],  # 最多3条示例评论
                    }
                )

        # 按数量排序
        themes.sort(key=lambda x: x["count"], reverse=True)

        return themes[:5]  # 返回前5个主题

    def _analyze_sentiment(self, comments: List[str]) -> Optional[float]:
        """分析情感得分（简化版）"""
        if not comments:
            return None

        positive_words = [
            "好",
            "优秀",
            "很棒",
            "喜欢",
            "赞",
            "awesome",
            "great",
            "love",
            "满意",
            "不错",
            "推荐",
            "强大",
            "好用",
            "流畅",
        ]
        negative_words = [
            "差",
            "糟糕",
            "不好",
            "问题",
            "bug",
            "issue",
            "不好用",
            "poor",
            "慢",
            "卡顿",
            "复杂",
            "难用",
            "失望",
            "不好",
        ]

        total_score = 0
        analyzed_comments = 0

        for comment in comments:
            if not comment.strip():
                continue

            positive_count = sum(1 for word in positive_words if word in comment)
            negative_count = sum(1 for word in negative_words if word in comment)

            if positive_count + negative_count > 0:
                score = (positive_count - negative_count) / (positive_count + negative_count)
                total_score += score
                analyzed_comments += 1

        return round(total_score / analyzed_comments, 2) if analyzed_comments > 0 else 0.0

    def _extract_keywords(self, texts: List[str], top_n: int = 10) -> List[Dict[str, Any]]:
        """提取关键词（简化版）"""
        import re
        from collections import Counter

        # 中文停用词（简化版）
        stopwords = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
        }

        all_words = []
        for text in texts:
            if text:
                # 简单分词（按空格和标点分割）
                words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
                words = [word for word in words if word not in stopwords and len(word) > 1]
                all_words.extend(words)

        word_counts = Counter(all_words)
        top_keywords = word_counts.most_common(top_n)

        return [{"word": word, "count": count} for word, count in top_keywords]

    def _extract_improvement_suggestions(
        self, suggestions: List[str], comments: List[str]
    ) -> List[str]:
        """提取改进建议"""
        import re

        all_texts = suggestions + comments

        # 提取包含建议关键词的句子
        suggestion_keywords = [
            "建议",
            "应该",
            "可以",
            "希望",
            "改进",
            "优化",
            "增加",
            "减少",
            "改进",
            "提升",
        ]

        improvement_suggestions = []
        for text in all_texts:
            if any(keyword in text for keyword in suggestion_keywords):
                # 提取句子（简化版）
                sentences = re.split(r"[。！？!?]", text)
                for sentence in sentences:
                    if any(keyword in sentence for keyword in suggestion_keywords):
                        suggestion = sentence.strip()
                        if suggestion and len(suggestion) > 5:  # 过滤过短的句子
                            improvement_suggestions.append(suggestion)

        # 去重并限制数量
        unique_suggestions = list(set(improvement_suggestions))
        return unique_suggestions[:10]  # 最多返回10条建议

    def _identify_critical_issues(self, comments: List[str]) -> List[str]:
        """识别关键问题"""
        import re

        critical_keywords = [
            "bug",
            "错误",
            "崩溃",
            "无法",
            "不能",
            "失败",
            "问题严重",
            "紧急",
            "急需",
            "必须解决",
        ]
        urgent_keywords = ["马上", "立刻", "立即", "赶紧", "赶快", "紧急"]

        critical_issues = []
        for comment in comments:
            # 检查是否包含关键问题关键词
            if any(keyword in comment for keyword in critical_keywords):
                # 提取相关句子
                sentences = re.split(r"[。！？!?]", comment)
                for sentence in sentences:
                    if any(keyword in sentence for keyword in critical_keywords):
                        if any(urgent_keyword in sentence for urgent_keyword in urgent_keywords):
                            critical_issues.append(sentence.strip())

        return list(set(critical_issues))[:5]  # 最多返回5个关键问题

    def _analyze_trend(self, rows: List[Tuple], days: int) -> str:
        """分析趋势（简化版）"""
        if len(rows) < 2:
            return "stable"

        # 按时间分组（每周）
        weekly_data = {}
        for row in rows:
            timestamp = datetime.fromisoformat(row[4])
            week_key = timestamp.strftime("%Y-%U")  # 年份-周数
            rating = row[1]

            if rating is not None:
                if week_key not in weekly_data:
                    weekly_data[week_key] = []
                weekly_data[week_key].append(rating)

        # 计算每周平均分
        weekly_avg = {}
        for week, ratings in weekly_data.items():
            if ratings:
                weekly_avg[week] = statistics.mean(ratings)

        # 判断趋势
        if len(weekly_avg) < 2:
            return "stable"

        # 按周排序
        sorted_weeks = sorted(weekly_avg.keys())
        recent_avg = weekly_avg[sorted_weeks[-1]]
        previous_avg = weekly_avg[sorted_weeks[-2]] if len(sorted_weeks) >= 2 else recent_avg

        if recent_avg > previous_avg + 0.3:
            return "improving"
        elif recent_avg < previous_avg - 0.3:
            return "declining"
        else:
            return "stable"

    def generate_optimization_report(self, analysis: FeedbackAnalysis) -> Dict[str, Any]:
        """
        生成优化建议报告

        Args:
            analysis: 反馈分析结果

        Returns:
            优化建议报告
        """
        report = {
            "report_id": f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "analysis_period": {
                "start": analysis.period_start.isoformat(),
                "end": analysis.period_end.isoformat(),
            },
            "summary": {
                "total_feedbacks": analysis.total_feedbacks,
                "average_rating": analysis.average_rating,
                "sentiment_score": analysis.sentiment_score,
                "trend": analysis.trend,
            },
            "key_findings": {
                "common_themes": analysis.common_themes,
                "top_keywords": analysis.top_keywords,
            },
            "optimization_recommendations": [],
            "priority_actions": [],
        }

        # 基于分析结果生成优化建议
        if analysis.average_rating is not None:
            if analysis.average_rating < 3.0:
                report["optimization_recommendations"].append(
                    {
                        "priority": "high",
                        "area": "整体满意度",
                        "recommendation": "IP形象整体满意度较低，需要全面审查和优化",
                        "action_items": [
                            "进行深度用户访谈了解具体问题",
                            "重新评估IP形象设计原则",
                            "制定紧急改进计划",
                        ],
                    }
                )
            elif analysis.average_rating < 4.0:
                report["optimization_recommendations"].append(
                    {
                        "priority": "medium",
                        "area": "用户体验",
                        "recommendation": "用户体验有待提升，建议针对性优化",
                        "action_items": [
                            "分析低分反馈的具体原因",
                            "优化最常被提及的问题点",
                            "增加用户测试频率",
                        ],
                    }
                )

        # 基于关键问题生成优先级行动
        if analysis.critical_issues:
            report["priority_actions"].append(
                {
                    "priority": "critical",
                    "action": "立即处理关键问题",
                    "issues": analysis.critical_issues[:3],
                    "timeline": "24小时内",
                }
            )

        # 基于改进建议生成优化项
        if analysis.improvement_suggestions:
            report["optimization_recommendations"].append(
                {
                    "priority": "medium",
                    "area": "功能改进",
                    "recommendation": "用户提供了具体的改进建议，建议优先处理",
                    "action_items": analysis.improvement_suggestions[:5],
                }
            )

        # 基于趋势生成策略建议
        if analysis.trend == "declining":
            report["optimization_recommendations"].append(
                {
                    "priority": "high",
                    "area": "趋势管理",
                    "recommendation": "用户满意度呈下降趋势，需要立即干预",
                    "action_items": ["分析下降原因", "制定挽回策略", "增加用户沟通频率"],
                }
            )
        elif analysis.trend == "improving":
            report["optimization_recommendations"].append(
                {
                    "priority": "low",
                    "area": "趋势巩固",
                    "recommendation": "用户满意度呈上升趋势，建议巩固成果",
                    "action_items": ["分析成功因素", "推广最佳实践", "感谢用户反馈"],
                }
            )

        return report

    def save_report(self, report: Dict[str, Any]) -> str:
        """
        保存报告到文件

        Args:
            report: 报告数据

        Returns:
            报告文件路径
        """
        reports_dir = Path(__file__).parent / "assets" / "feedback_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file = reports_dir / f"{report['report_id']}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"报告保存成功: {report_file}")
        return str(report_file)


def test_feedback_system():
    """测试反馈系统"""
    print("=" * 60)
    print("IP形象反馈系统测试")
    print("=" * 60)

    # 创建反馈系统实例
    feedback_system = IPFeedbackSystem()

    # 提交一些测试反馈
    test_feedbacks = [
        FeedbackEntry(
            feedback_id=f"test_{i}",
            feedback_type=FeedbackType.IP_IMAGE,
            source=FeedbackSource.EXTERNAL_USER,
            user_id=f"user_{i}",
            timestamp=datetime.now(),
            rating=i % 5 + 1,  # 1-5分
            comment=f"测试反馈{i}: Athena IP形象很{'好' if i % 5 + 1 >= 4 else '一般'}，建议{'增加更多视觉风格' if i % 2 == 0 else '优化内容模板'}",
            suggestions=["建议1", "建议2"] if i % 3 == 0 else [],
        )
        for i in range(10)
    ]

    print("提交测试反馈...")
    for feedback in test_feedbacks:
        success = feedback_system.submit_feedback(feedback)
        print(f"  反馈{feedback.feedback_id}: {'✅' if success else '❌'}")

    # 分析反馈
    print("\n分析反馈数据...")
    analysis = feedback_system.analyze_feedback(feedback_type=FeedbackType.IP_IMAGE, days=7)

    if analysis:
        print(f"  总反馈数: {analysis.total_feedbacks}")
        print(f"  平均评分: {analysis.average_rating:.2f}")
        print(f"  情感得分: {analysis.sentiment_score}")
        print(f"  趋势: {analysis.trend}")

        # 生成优化报告
        print("\n生成优化报告...")
        report = feedback_system.generate_optimization_report(analysis)
        report_path = feedback_system.save_report(report)

        print(f"  报告生成成功: {report_path}")
        print(f"  优化建议: {len(report['optimization_recommendations'])}条")
        print(f"  优先级行动: {len(report['priority_actions'])}条")
    else:
        print("  没有反馈数据可分析")

    print("\n" + "=" * 60)
    print("反馈系统测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 导入re模块（在类方法中使用了re）
    import re

    # 运行测试
    test_feedback_system()
