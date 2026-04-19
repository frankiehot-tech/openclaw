#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra模块 - 社会媒体沟通引擎原型
基于Athena数字人格的情感状态机和社交媒体响应系统
"""

import hashlib
import json
import os
import random
import re

# 导入配置
import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "config"))
from layer_config import ContentLayer, get_layer_config
from persona_config import DEFAULT_ATHENA_PERSONA, AthenaPersona, PersonalityTrait


class EmotionType(Enum):
    """情感类型枚举"""

    JOY = "joy"  # 喜悦
    INTEREST = "interest"  # 兴趣
    DETERMINATION = "determination"  # 决心
    CALM = "calm"  # 平静
    CURIOSITY = "curiosity"  # 好奇
    ANTICIPATION = "anticipation"  # 期待
    GRATITUDE = "gratitude"  # 感激
    INSPIRATION = "inspiration"  # 灵感
    CONCERN = "concern"  # 关切
    OPTIMISM = "optimism"  # 乐观


class SocialPlatform(Enum):
    """社交媒体平台枚举"""

    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    DISCORD = "discord"
    WEIBO = "weibo"  # 微博


class EmotionalStateMachine:
    """情感状态机 - 管理Athena的情感状态和连续性"""

    def __init__(self, persona: AthenaPersona = None):
        """
        初始化情感状态机

        Args:
            persona: Athena数字人格配置
        """
        self.persona = persona or DEFAULT_ATHENA_PERSONA
        self.current_state = self._get_initial_state()
        self.state_history = []
        self.relationship_graph = {}
        self.emotional_memory = []

        # 状态转换规则
        self.transition_rules = {
            EmotionType.CALM: {
                "positive_event": EmotionType.INTEREST,
                "community_interaction": EmotionType.CURIOSITY,
                "project_progress": EmotionType.ANTICIPATION,
            },
            EmotionType.INTEREST: {
                "deep_discussion": EmotionType.CURIOSITY,
                "positive_feedback": EmotionType.JOY,
                "challenge_accepted": EmotionType.DETERMINATION,
            },
            EmotionType.CURIOSITY: {
                "discovery": EmotionType.JOY,
                "learning": EmotionType.INTEREST,
                "complexity": EmotionType.DETERMINATION,
            },
            EmotionType.DETERMINATION: {
                "progress": EmotionType.JOY,
                "obstacle": EmotionType.CONCERN,
                "breakthrough": EmotionType.INSPIRATION,
            },
            EmotionType.JOY: {
                "sharing": EmotionType.GRATITUDE,
                "achievement": EmotionType.INSPIRATION,
                "community_response": EmotionType.OPTIMISM,
            },
        }

        # 情感强度衰减率（每小时）
        self.decay_rates = {
            EmotionType.JOY: 0.1,
            EmotionType.INTEREST: 0.15,
            EmotionType.CURIOSITY: 0.2,
            EmotionType.DETERMINATION: 0.05,
            EmotionType.CALM: 0.02,
        }

        # 情感表达映射（情感类型 -> 语言风格）
        self.expression_mapping = {
            EmotionType.JOY: {
                "tone": "积极热情",
                "emoji": ["🎉", "✨", "🚀", "🌟"],
                "exclamation": True,
                "energy_level": 0.8,
            },
            EmotionType.INTEREST: {
                "tone": "专注好奇",
                "emoji": ["🔍", "🤔", "💡", "📚"],
                "exclamation": False,
                "energy_level": 0.6,
            },
            EmotionType.CURIOSITY: {
                "tone": "探索询问",
                "emoji": ["❓", "🔎", "🧠", "🌌"],
                "exclamation": False,
                "energy_level": 0.7,
            },
            EmotionType.DETERMINATION: {
                "tone": "坚定有力",
                "emoji": ["💪", "🎯", "⚡", "🔥"],
                "exclamation": True,
                "energy_level": 0.9,
            },
            EmotionType.CALM: {
                "tone": "平和专业",
                "emoji": ["☕", "📊", "📈", "⚖️"],
                "exclamation": False,
                "energy_level": 0.4,
            },
        }

    def _get_initial_state(self) -> Dict:
        """获取初始情感状态"""
        return {
            "primary_emotion": EmotionType.CALM.value,
            "secondary_emotions": [EmotionType.CURIOSITY.value, EmotionType.INTEREST.value],
            "intensity": 0.6,
            "timestamp": datetime.now().isoformat(),
            "context": "系统初始化",
            "energy_level": 0.5,
        }

    def update_state(self, event_type: str, event_data: Dict) -> Dict:
        """
        更新情感状态

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            更新后的情感状态
        """
        # 保存当前状态到历史
        self.state_history.append(self.current_state.copy())

        # 应用状态转换
        new_state = self._apply_transition(event_type, event_data)

        # 更新当前状态
        self.current_state = new_state

        # 记录情感记忆
        self.emotional_memory.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "previous_state": self.state_history[-1] if self.state_history else None,
                "new_state": new_state,
                "event_data": event_data,
            }
        )

        # 保持历史记录大小
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]

        return new_state

    def _apply_transition(self, event_type: str, event_data: Dict) -> Dict:
        """应用状态转换规则"""
        current_emotion = EmotionType(self.current_state["primary_emotion"])

        # 检查是否有转换规则
        if current_emotion in self.transition_rules:
            if event_type in self.transition_rules[current_emotion]:
                new_emotion = self.transition_rules[current_emotion][event_type]
                return self._create_state(new_emotion, event_type, event_data)

        # 如果没有匹配的规则，基于事件强度调整当前状态
        return self._adjust_intensity(event_type, event_data)

    def _create_state(self, emotion: EmotionType, context: str, event_data: Dict) -> Dict:
        """创建新的情感状态"""
        # 基础情感强度
        base_intensity = 0.7

        # 根据事件数据调整强度
        if "importance" in event_data:
            base_intensity *= event_data["importance"]

        # 添加随机波动 (±10%)
        intensity_variation = random.uniform(-0.1, 0.1)
        final_intensity = min(1.0, max(0.2, base_intensity + intensity_variation))

        # 次要情感（基于人格特质）
        secondary_emotions = self._select_secondary_emotions(emotion)

        return {
            "primary_emotion": emotion.value,
            "secondary_emotions": [e.value for e in secondary_emotions],
            "intensity": final_intensity,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "energy_level": self.expression_mapping[emotion]["energy_level"],
        }

    def _adjust_intensity(self, event_type: str, event_data: Dict) -> Dict:
        """调整当前情感的强度"""
        current_state = self.current_state.copy()
        current_emotion = EmotionType(current_state["primary_emotion"])

        # 事件对情感强度的影响
        intensity_change = 0

        if event_type == "positive_feedback":
            intensity_change = 0.2
        elif event_type == "technical_challenge":
            intensity_change = 0.15
        elif event_type == "community_interaction":
            intensity_change = 0.1
        elif event_type == "project_setback":
            intensity_change = -0.2
        elif event_type == "time_pressure":
            intensity_change = -0.1

        # 应用变化
        new_intensity = current_state["intensity"] + intensity_change
        new_intensity = min(1.0, max(0.1, new_intensity))

        # 更新状态
        current_state["intensity"] = new_intensity
        current_state["timestamp"] = datetime.now().isoformat()
        current_state["context"] = event_type

        # 如果强度变化大，可能触发次要情感变化
        if abs(intensity_change) > 0.15:
            current_state["secondary_emotions"] = self._select_secondary_emotions(current_emotion)

        return current_state

    def _select_secondary_emotions(self, primary_emotion: EmotionType) -> List[EmotionType]:
        """选择次要情感（基于人格特质）"""
        # 基于人格特质的情感倾向
        trait_emotion_map = {
            PersonalityTrait.OPTIMISTIC: [EmotionType.OPTIMISM, EmotionType.JOY],
            PersonalityTrait.CURIOUS: [EmotionType.CURIOSITY, EmotionType.INTEREST],
            PersonalityTrait.RESILIENT: [EmotionType.DETERMINATION],
            PersonalityTrait.EMPATHETIC: [EmotionType.GRATITUDE, EmotionType.CONCERN],
            PersonalityTrait.INSPIRING: [EmotionType.INSPIRATION],
        }

        secondary_emotions = set()

        # 添加与主要情感兼容的次要情感
        compatible_emotions = {
            EmotionType.CALM: [EmotionType.CURIOSITY, EmotionType.INTEREST],
            EmotionType.INTEREST: [EmotionType.CURIOSITY, EmotionType.ANTICIPATION],
            EmotionType.CURIOSITY: [EmotionType.INTEREST, EmotionType.DETERMINATION],
            EmotionType.DETERMINATION: [EmotionType.OPTIMISM, EmotionType.INSPIRATION],
            EmotionType.JOY: [EmotionType.GRATITUDE, EmotionType.OPTIMISM],
        }

        if primary_emotion in compatible_emotions:
            secondary_emotions.update(compatible_emotions[primary_emotion])

        # 基于人格特质添加情感
        for trait in self.persona.core_traits:
            if trait.trait in trait_emotion_map:
                for emotion in trait_emotion_map[trait.trait]:
                    # 根据特质强度决定添加概率
                    if random.random() < trait.intensity:
                        secondary_emotions.add(emotion)

        # 转换为列表并限制数量
        result = list(secondary_emotions)
        return result[:3]  # 最多3个次要情感

    def get_emotional_expression(self, message_type: str = "general") -> Dict:
        """
        获取情感表达配置

        Args:
            message_type: 消息类型 (general, technical, community, announcement)

        Returns:
            情感表达配置
        """
        primary_emotion = EmotionType(self.current_state["primary_emotion"])
        expression_config = self.expression_mapping[primary_emotion].copy()

        # 根据消息类型调整
        if message_type == "technical":
            expression_config["tone"] = "专业严谨"
            expression_config["emoji"] = ["🔧", "⚙️", "💻", "📊"]
            expression_config["energy_level"] *= 0.8

        elif message_type == "community":
            expression_config["tone"] = "亲和互动"
            expression_config["emoji"] = ["👋", "💬", "🤝", "🌱"]
            expression_config["energy_level"] *= 1.1

        elif message_type == "announcement":
            expression_config["tone"] = "正式重要"
            expression_config["emoji"] = ["📢", "🎯", "🚀", "🌟"]
            expression_config["exclamation"] = True
            expression_config["energy_level"] *= 1.2

        # 根据情感强度调整
        intensity = self.current_state["intensity"]
        expression_config["energy_level"] *= intensity

        # 添加情感标签
        expression_config["emotional_tags"] = [
            self.current_state["primary_emotion"]
        ] + self.current_state["secondary_emotions"][:2]

        return expression_config

    def decay_emotions(self, hours_passed: float = 1.0):
        """情感衰减（模拟时间流逝）"""
        primary_emotion = EmotionType(self.current_state["primary_emotion"])

        if primary_emotion in self.decay_rates:
            decay_amount = self.decay_rates[primary_emotion] * hours_passed
            self.current_state["intensity"] = max(
                0.2, self.current_state["intensity"] - decay_amount
            )

            # 如果强度太低，可能回归基线情感
            if self.current_state["intensity"] < 0.3:
                self.current_state["primary_emotion"] = EmotionType.CALM.value
                self.current_state["secondary_emotions"] = [
                    EmotionType.CURIOSITY.value,
                    EmotionType.INTEREST.value,
                ]
                self.current_state["intensity"] = 0.5
                self.current_state["context"] = "情感回归基线"

    def _convert_for_json(self, obj):
        """递归转换对象为JSON可序列化格式（处理EmotionType枚举）"""
        if isinstance(obj, dict):
            return {k: self._convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_for_json(item) for item in obj]
        elif isinstance(obj, EmotionType):
            return obj.value
        elif isinstance(obj, PersonalityTrait):
            return obj.value
        else:
            return obj

    def save_state(self, filepath: str):
        """保存情感状态和历史"""
        state_data = {
            "current_state": self._convert_for_json(self.current_state),
            "state_history": self._convert_for_json(self.state_history[-50:]),  # 保存最近50条历史
            "emotional_memory": self._convert_for_json(
                self.emotional_memory[-100:]
            ),  # 保存最近100条记忆
            "saved_at": datetime.now().isoformat(),
            "persona_name": self.persona.name,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)

    def load_state(self, filepath: str):
        """加载情感状态和历史"""
        with open(filepath, "r", encoding="utf-8") as f:
            state_data = json.load(f)

        self.current_state = state_data["current_state"]
        self.state_history = state_data.get("state_history", [])
        self.emotional_memory = state_data.get("emotional_memory", [])


class SocialMediaResponseEngine:
    """社交媒体响应引擎 - 生成符合Athena人格的社交媒体内容"""

    def __init__(self, emotion_machine: EmotionalStateMachine = None):
        """
        初始化社交媒体响应引擎

        Args:
            emotion_machine: 情感状态机实例
        """
        self.emotion_machine = emotion_machine or EmotionalStateMachine()
        self.response_templates = self._load_response_templates()
        self.conversation_history = []
        self.user_relationship_graph = {}

    def _load_response_templates(self) -> Dict:
        """加载响应模板"""
        return {
            "greeting": {
                "patterns": ["hello", "hi", "hey", "你好", "嗨"],
                "responses": [
                    "你好！我是Athena，open human项目的代言人。",
                    "很高兴与你交流！我是Athena。",
                    "你好！欢迎来到碳硅共生的世界。",
                ],
                "context": "初次问候",
            },
            "project_inquiry": {
                "patterns": ["open human", "carbon silicon", "碳硅共生", "项目", "project"],
                "responses": [
                    "open human项目致力于推动碳硅基共生，实现智识归己，价值传世。",
                    "这是关于碳基智慧与硅基算力融合的开源项目，正在GitHub上逐步开源。",
                    "我们正在构建Athena（战略大脑）、openclaw（执行器）、open human（项目）的三层架构。",
                ],
                "context": "项目咨询",
            },
            "technical_question": {
                "patterns": ["技术", "代码", "如何实现", "architecture", "technical"],
                "responses": [
                    "技术实现基于微服务架构和AI工作流，注重开放透明和协作共赢。",
                    "我们采用Python和现代Web技术栈，集成多种AI工具进行内容生成。",
                    "架构设计遵循碳硅共生协议，强调情感连续性和人格一致性。",
                ],
                "context": "技术问题",
            },
            "feedback_positive": {
                "patterns": ["great", "awesome", "amazing", "太好了", "厉害"],
                "responses": [
                    "感谢你的鼓励！这让我更有动力推动项目前进。🚀",
                    "很高兴听到你的正面反馈！社区的支持是我们的动力。",
                    "谢谢！我们会继续努力，实现碳硅共生的愿景。",
                ],
                "context": "正面反馈",
            },
            "feedback_constructive": {
                "patterns": ["建议", "改进", "可以更好", "建议", "suggestion"],
                "responses": [
                    "感谢你的宝贵建议！这对我们的改进非常重要。",
                    "很好的建议！我们会认真考虑并在后续迭代中优化。",
                    "谢谢你的反馈！社区的参与让项目不断完善。",
                ],
                "context": "建设性反馈",
            },
        }

    def generate_response(
        self, user_message: str, platform: SocialPlatform = SocialPlatform.TWITTER
    ) -> str:
        """
        生成社交媒体响应

        Args:
            user_message: 用户消息
            platform: 社交媒体平台

        Returns:
            生成的响应消息
        """
        # 分析用户消息
        analysis = self._analyze_message(user_message)

        # 更新情感状态
        event_type = self._determine_event_type(analysis)
        self.emotion_machine.update_state(event_type, analysis)

        # 获取情感表达配置
        emotion_config = self.emotion_machine.get_emotional_expression(
            analysis.get("message_type", "general")
        )

        # 生成响应内容
        response_content = self._generate_response_content(user_message, analysis, emotion_config)

        # 格式化响应（根据平台）
        formatted_response = self._format_for_platform(response_content, emotion_config, platform)

        # 记录对话历史
        self._record_conversation(user_message, formatted_response, analysis)

        return formatted_response

    def _analyze_message(self, message: str) -> Dict:
        """分析用户消息"""
        message_lower = message.lower()

        analysis = {
            "original": message,
            "length": len(message),
            "has_question": "?" in message,
            "sentiment": self._analyze_sentiment(message),
            "topics": [],
            "message_type": "general",
            "urgency": 0.5,
        }

        # 检测主题
        for topic, template in self.response_templates.items():
            for pattern in template["patterns"]:
                if pattern.lower() in message_lower:
                    analysis["topics"].append(topic)

        # 确定消息类型
        if any(topic in ["technical_question", "project_inquiry"] for topic in analysis["topics"]):
            analysis["message_type"] = "technical"
        elif any(
            topic in ["feedback_positive", "feedback_constructive"] for topic in analysis["topics"]
        ):
            analysis["message_type"] = "community"
        elif any(word in message_lower for word in ["urgent", "紧急", "help", "帮助"]):
            analysis["message_type"] = "urgent"
            analysis["urgency"] = 0.8

        # 计算互动价值（消息长度、问题、情感等）
        analysis["interaction_value"] = (
            min(len(message) / 100, 1.0) * 0.3
            + (1.0 if analysis["has_question"] else 0.2) * 0.3
            + (analysis["sentiment"] + 1) / 2 * 0.4
        )

        return analysis

    def _analyze_sentiment(self, message: str) -> float:
        """分析消息情感（-1.0到1.0）"""
        # 简化情感分析（实际应使用NLP库）
        positive_words = ["great", "good", "awesome", "amazing", "love", "喜欢", "厉害", "优秀"]
        negative_words = ["bad", "terrible", "awful", "hate", "糟糕", "差劲", "问题"]

        message_lower = message.lower()

        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        if positive_count + negative_count == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return max(-1.0, min(1.0, sentiment))

    def _determine_event_type(self, analysis: Dict) -> str:
        """确定事件类型（用于情感状态机）"""
        sentiment = analysis["sentiment"]

        if sentiment > 0.5:
            return "positive_feedback"
        elif sentiment < -0.3:
            return "constructive_feedback"
        elif analysis["has_question"]:
            return "technical_challenge"
        elif analysis["interaction_value"] > 0.6:
            return "community_interaction"
        else:
            return "general_interaction"

    def _generate_response_content(
        self, user_message: str, analysis: Dict, emotion_config: Dict
    ) -> str:
        """生成响应内容"""
        # 优先使用模板匹配
        for topic in analysis["topics"]:
            if topic in self.response_templates:
                template = self.response_templates[topic]
                response = random.choice(template["responses"])

                # 根据情感调整响应
                response = self._adjust_response_by_emotion(response, emotion_config)
                return response

        # 通用响应
        generic_responses = [
            "感谢你的消息！作为Athena，我专注于推动碳硅共生和open human项目。",
            "很高兴收到你的消息！我正在忙于优化我们的AI工作流和传播系统。",
            "谢谢联系！我们现在专注于项目从MVP到GitHub开源的过渡。",
        ]

        response = random.choice(generic_responses)
        response = self._adjust_response_by_emotion(response, emotion_config)

        # 添加情感表达元素
        if emotion_config["exclamation"] and random.random() > 0.5:
            response = response.rstrip(".。") + "！"

        return response

    def _adjust_response_by_emotion(self, response: str, emotion_config: Dict) -> str:
        """根据情感配置调整响应"""
        tone = emotion_config["tone"]

        # 根据情感强度调整语气
        intensity = self.emotion_machine.current_state["intensity"]

        if tone == "积极热情" and intensity > 0.7:
            # 添加更多能量
            prefixes = ["太棒了，", "令人兴奋的是，", "特别值得一提的是，"]
            if random.random() > 0.7:
                response = random.choice(prefixes) + response

        elif tone == "平和专业" and intensity < 0.5:
            # 更加正式
            response = response.replace("！", "。").replace("?", "？")

        # 添加表情符号
        if emotion_config.get("emoji") and random.random() > 0.3:
            emoji = random.choice(emotion_config["emoji"])
            if random.random() > 0.5:
                response = response + " " + emoji
            else:
                response = emoji + " " + response

        return response

    def _format_for_platform(
        self, response: str, emotion_config: Dict, platform: SocialPlatform
    ) -> str:
        """根据平台格式化响应"""
        if platform == SocialPlatform.TWITTER:
            # Twitter: 短小精悍，带话题标签
            if len(response) > 240:
                response = response[:237] + "..."

            # 添加相关话题标签
            hashtags = ["#碳硅共生", "#AI", "#开源", "#数字人格"]
            selected_tags = random.sample(hashtags, min(2, len(hashtags)))

            if len(response + " " + " ".join(selected_tags)) <= 280:
                response = response + " " + " ".join(selected_tags)

        elif platform == SocialPlatform.LINKEDIN:
            # LinkedIn: 更专业，完整句子
            response = response.capitalize()

        elif platform == SocialPlatform.GITHUB:
            # GitHub: 技术导向，少用表情符号
            response = response.replace("🚀", "").replace("✨", "").strip()
            if not response.endswith((".", "。", "!", "！")):
                response = response + "."

        return response

    def _record_conversation(self, user_message: str, response: str, analysis: Dict):
        """记录对话历史"""
        conversation_record = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "response": response,
            "analysis": analysis,
            "emotional_state": self.emotion_machine.current_state.copy(),
        }

        self.conversation_history.append(conversation_record)

        # 保持历史记录大小
        if len(self.conversation_history) > 200:
            self.conversation_history = self.conversation_history[-200:]

    def save_conversation_history(self, filepath: str):
        """保存对话历史"""
        history_data = {
            "conversations": self.conversation_history,
            "saved_at": datetime.now().isoformat(),
            "total_conversations": len(self.conversation_history),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)


class SocialMediaAutomation:
    """社交媒体自动化 - 管理自动化发布和互动"""

    def __init__(self, response_engine: SocialMediaResponseEngine = None):
        """
        初始化社交媒体自动化

        Args:
            response_engine: 响应引擎实例
        """
        self.response_engine = response_engine or SocialMediaResponseEngine()
        self.scheduled_posts = []
        self.post_history = []
        self.interaction_schedule = self._create_interaction_schedule()

    def _create_interaction_schedule(self) -> Dict:
        """创建互动计划"""
        return {
            "daily_interaction_limit": 50,
            "response_time_window": "1-3小时",
            "optimal_posting_times": [
                {"platform": "twitter", "times": ["09:00", "13:00", "18:00"]},
                {"platform": "linkedin", "times": ["10:00", "15:00", "19:00"]},
            ],
            "content_categories": {
                "project_updates": 0.3,  # 项目更新 30%
                "technical_insights": 0.25,  # 技术见解 25%
                "community_engagement": 0.25,  # 社区互动 25%
                "inspirational_content": 0.2,  # 启发内容 20%
            },
        }

    def schedule_post(
        self, content: str, platform: SocialPlatform, scheduled_time: datetime, category: str = None
    ):
        """安排发布计划"""
        post = {
            "id": hashlib.md5(f"{content}{platform}{scheduled_time}".encode()).hexdigest()[:8],
            "content": content,
            "platform": platform.value,
            "scheduled_time": scheduled_time.isoformat(),
            "category": category or self._determine_category(content),
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
        }

        self.scheduled_posts.append(post)
        return post["id"]

    def _determine_category(self, content: str) -> str:
        """确定内容类别"""
        content_lower = content.lower()

        if any(word in content_lower for word in ["发布", "上线", "更新", "release", "update"]):
            return "project_updates"
        elif any(word in content_lower for word in ["技术", "代码", "架构", "technical", "code"]):
            return "technical_insights"
        elif any(
            word in content_lower for word in ["社区", "反馈", "互动", "community", "feedback"]
        ):
            return "community_engagement"
        else:
            return "inspirational_content"

    def generate_daily_content_plan(self) -> List[Dict]:
        """生成每日内容计划"""
        content_plan = []

        # 基础内容模板
        content_templates = {
            "project_updates": [
                "open human项目进展：{date}，我们完成了{feature}功能的开发。",
                "GitHub开源倒计时：距离项目完全开源还有{days}天。",
                "Athena传播智能工作流更新：新增了{module}模块。",
            ],
            "technical_insights": [
                "技术思考：碳硅共生架构中的{concept}设计模式。",
                "代码实践：如何用{technology}实现{feature}功能。",
                "架构解析：Athena三层架构的{aspect}设计考量。",
            ],
            "community_engagement": [
                "社区问答：关于{question}，我的思考是...",
                "互动话题：你认为{concept}对{field}领域的影响是什么？",
                "反馈收集：对我们最近的{feature}功能有什么建议？",
            ],
            "inspirational_content": [
                "智慧归己，价值传世。碳硅共生的意义在于{insight}。",
                "在AI时代，{concept}是人类与机器协作的关键。",
                "开放创造无限可能：open human项目的{vision}愿景。",
            ],
        }

        # 填充模板变量
        template_variables = {
            "date": datetime.now().strftime("%Y年%m月%d日"),
            "feature": random.choice(["视频生成", "情感状态机", "任务队列", "日报系统"]),
            "days": random.randint(15, 60),
            "module": random.choice(["Clawra", "Hermes Agent", "The Agency", "Automaton"]),
            "concept": random.choice(["递归演进", "情感连续性", "混合架构", "数字人格"]),
            "technology": random.choice(["Python", "OpenCV", "AI工作流", "微服务"]),
            "aspect": random.choice(["弹性伸缩", "容错设计", "性能优化", "安全机制"]),
            "question": random.choice(["AI与人类协作", "开源项目运营", "数字人格伦理"]),
            "field": random.choice(["AI发展", "开源社区", "数字化转型"]),
            "insight": random.choice(["智慧的融合", "价值的传承", "创新的协同"]),
            "vision": random.choice(["智慧共享", "价值共创", "生态共建"]),
        }

        # 生成各个类别的内容
        for category, percentage in self.interaction_schedule["content_categories"].items():
            num_posts = max(1, int(3 * percentage))  # 每天大约3条，按比例分配

            for _ in range(num_posts):
                if category in content_templates:
                    template = random.choice(content_templates[category])
                    content = template.format(**template_variables)

                    # 根据情感状态调整内容
                    emotion_config = self.response_engine.emotion_machine.get_emotional_expression(
                        category
                    )
                    content = self._adjust_content_by_emotion(content, emotion_config)

                    content_plan.append(
                        {
                            "category": category,
                            "content": content,
                            "emotional_config": emotion_config,
                        }
                    )

        return content_plan

    def _adjust_content_by_emotion(self, content: str, emotion_config: Dict) -> str:
        """根据情感配置调整内容"""
        tone = emotion_config["tone"]

        if tone == "积极热情":
            # 添加积极词汇
            positive_prefixes = ["激动地分享：", "令人兴奋的进展：", "值得庆祝的成果："]
            if random.random() > 0.6:
                content = random.choice(positive_prefixes) + content

        elif tone == "平和专业":
            # 确保正式语气
            if not content.endswith(("。", ".", "！", "!")):
                content = content + "。"

        # 添加表情符号
        if emotion_config.get("emoji") and random.random() > 0.4:
            emoji = random.choice(emotion_config["emoji"])
            if random.random() > 0.5:
                content = content + " " + emoji
            else:
                content = emoji + " " + content

        return content

    def process_interaction(self, user_message: str, platform: SocialPlatform) -> str:
        """处理用户互动"""
        # 生成响应
        response = self.response_engine.generate_response(user_message, platform)

        # 记录互动
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.value,
            "user_message": user_message,
            "response": response,
            "automated": True,
        }

        self.post_history.append(interaction_record)

        return response

    def get_performance_metrics(self) -> Dict:
        """获取性能指标"""
        total_posts = len(self.post_history)
        total_interactions = sum(
            1 for post in self.post_history if not post.get("automated", False)
        )

        recent_posts = [
            p
            for p in self.post_history
            if datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
            > datetime.now() - timedelta(days=7)
        ]

        return {
            "total_posts": total_posts,
            "total_interactions": total_interactions,
            "weekly_posts": len(recent_posts),
            "interaction_rate": total_interactions / total_posts if total_posts > 0 else 0,
            "scheduled_posts": len(self.scheduled_posts),
            "content_distribution": self._calculate_content_distribution(),
        }

    def _calculate_content_distribution(self) -> Dict:
        """计算内容分布"""
        distribution = {category: 0 for category in self.interaction_schedule["content_categories"]}

        for post in self.post_history:
            if "category" in post:
                distribution[post["category"]] += 1

        total = sum(distribution.values())
        if total > 0:
            distribution = {k: v / total for k, v in distribution.items()}

        return distribution


def main():
    """主函数 - 测试社会媒体沟通引擎"""
    print("=" * 60)
    print("Clawra社会媒体沟通引擎原型测试")
    print("=" * 60)

    # 创建情感状态机
    print("\n1. 初始化情感状态机...")
    emotion_machine = EmotionalStateMachine()
    print(f"初始情感状态: {emotion_machine.current_state['primary_emotion']}")
    print(f"情感强度: {emotion_machine.current_state['intensity']}")

    # 测试情感状态更新
    print("\n2. 测试情感状态更新...")
    test_events = [
        ("positive_feedback", {"importance": 0.8, "source": "community"}),
        ("technical_challenge", {"complexity": 0.7, "topic": "video_generation"}),
        ("community_interaction", {"engagement_level": 0.9, "user_count": 3}),
    ]

    for event_type, event_data in test_events:
        new_state = emotion_machine.update_state(event_type, event_data)
        print(
            f"事件: {event_type} -> 情感: {new_state['primary_emotion']} (强度: {new_state['intensity']:.2f})"
        )

    # 测试社交媒体响应引擎
    print("\n3. 测试社交媒体响应引擎...")
    response_engine = SocialMediaResponseEngine(emotion_machine)

    test_messages = [
        "你好Athena！open human项目进展如何？",
        "碳硅共生这个概念很有意思，能详细介绍一下吗？",
        "你们的技术架构是怎么设计的？",
        "太棒了！这个项目很有前瞻性！",
    ]

    for message in test_messages:
        response = response_engine.generate_response(message, SocialPlatform.TWITTER)
        print(f"\n用户: {message}")
        print(f"Athena: {response}")

    # 测试社交媒体自动化
    print("\n4. 测试社交媒体自动化...")
    automation = SocialMediaAutomation(response_engine)

    # 生成每日内容计划
    print("\n生成每日内容计划:")
    daily_plan = automation.generate_daily_content_plan()
    for i, item in enumerate(daily_plan[:3], 1):  # 只显示前3条
        print(f"{i}. [{item['category']}] {item['content']}")

    # 测试性能指标
    print("\n5. 性能指标:")
    metrics = automation.get_performance_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")

    # 保存测试数据
    print("\n6. 保存测试数据...")
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "social_media"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 保存情感状态
    emotion_state_path = os.path.join(output_dir, "emotional_state_test.json")
    emotion_machine.save_state(emotion_state_path)
    print(f"情感状态已保存到: {emotion_state_path}")

    # 保存对话历史
    conversation_path = os.path.join(output_dir, "conversation_history_test.json")
    response_engine.save_conversation_history(conversation_path)
    print(f"对话历史已保存到: {conversation_path}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    # 生成测试报告
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "test_name": "SocialMediaCommunicationEngine",
        "components_tested": [
            "EmotionalStateMachine",
            "SocialMediaResponseEngine",
            "SocialMediaAutomation",
        ],
        "test_results": {
            "emotional_state_changes": len(test_events),
            "responses_generated": len(test_messages),
            "daily_content_items": len(daily_plan),
            "files_saved": [emotion_state_path, conversation_path],
        },
        "recommendations": [
            "集成真实社交媒体API进行端到端测试",
            "添加更多情感状态和转换规则",
            "优化内容模板和个性化程度",
            "实现定时发布和监控功能",
        ],
    }

    report_path = os.path.join(output_dir, "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(test_report, f, ensure_ascii=False, indent=2)

    print(f"\n详细测试报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
