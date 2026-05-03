#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra模块 - 八层传播体系配置
参考碳硅共生协议八层传播体系设计
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class ContentLayer(Enum):
    """八层传播内容层级"""

    L1_5_SECONDS = "L1"  # 5秒层 - 瞬时冲击
    L2_5_MINUTES = "L2"  # 5分钟层 - 快速解释
    L3_1_HOUR = "L3"  # 1小时层 - 故事叙述
    L4_1_DAY = "L4"  # 1天层 - 深度纪录片
    L5_1_WEEK = "L5"  # 1周层 - 课程培训
    L6_1_MONTH = "L6"  # 1月层 - 专题研究
    L7_1_SEASON = "L7"  # 1季度层 - 战略规划
    L8_LIFETIME = "L8"  # 终身层 - 传承之环


@dataclass
class LayerConfig:
    """层级配置"""

    layer: ContentLayer
    duration_seconds: int
    content_type: str
    emotional_intensity: float  # 0.0-1.0
    cognitive_load: float  # 0.0-1.0
    production_time_min: int  # 预估生产时间（分钟）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer.value,
            "duration_seconds": self.duration_seconds,
            "content_type": self.content_type,
            "emotional_intensity": self.emotional_intensity,
            "cognitive_load": self.cognitive_load,
            "production_time_min": self.production_time_min,
        }


# 八层传播体系配置
LAYER_CONFIGS = {
    ContentLayer.L1_5_SECONDS: LayerConfig(
        layer=ContentLayer.L1_5_SECONDS,
        duration_seconds=5,
        content_type="短视频片段",
        emotional_intensity=0.9,
        cognitive_load=0.1,
        production_time_min=1,
    ),
    ContentLayer.L2_5_MINUTES: LayerConfig(
        layer=ContentLayer.L2_5_MINUTES,
        duration_seconds=300,
        content_type="快速解释视频",
        emotional_intensity=0.7,
        cognitive_load=0.3,
        production_time_min=15,
    ),
    ContentLayer.L3_1_HOUR: LayerConfig(
        layer=ContentLayer.L3_1_HOUR,
        duration_seconds=3600,
        content_type="故事叙述视频",
        emotional_intensity=0.6,
        cognitive_load=0.5,
        production_time_min=60,
    ),
    ContentLayer.L4_1_DAY: LayerConfig(
        layer=ContentLayer.L4_1_DAY,
        duration_seconds=86400,
        content_type="深度纪录片",
        emotional_intensity=0.5,
        cognitive_load=0.8,
        production_time_min=480,
    ),
    ContentLayer.L5_1_WEEK: LayerConfig(
        layer=ContentLayer.L5_1_WEEK,
        duration_seconds=604800,
        content_type="课程培训系列",
        emotional_intensity=0.4,
        cognitive_load=0.9,
        production_time_min=2400,
    ),
    ContentLayer.L6_1_MONTH: LayerConfig(
        layer=ContentLayer.L6_1_MONTH,
        duration_seconds=2592000,
        content_type="专题研究报告",
        emotional_intensity=0.3,
        cognitive_load=0.95,
        production_time_min=9600,
    ),
    ContentLayer.L7_1_SEASON: LayerConfig(
        layer=ContentLayer.L7_1_SEASON,
        duration_seconds=7776000,
        content_type="战略规划白皮书",
        emotional_intensity=0.2,
        cognitive_load=0.98,
        production_time_min=28800,
    ),
    ContentLayer.L8_LIFETIME: LayerConfig(
        layer=ContentLayer.L8_LIFETIME,
        duration_seconds=31536000,  # 1年作为代表
        content_type="传承之环作品",
        emotional_intensity=0.1,
        cognitive_load=1.0,
        production_time_min=115200,
    ),
}


def get_layer_config(layer: ContentLayer) -> LayerConfig:
    """获取指定层级的配置"""
    return LAYER_CONFIGS[layer]


def get_mvp_layer() -> ContentLayer:
    """获取MVP目标层级 - L3 1小时层"""
    return ContentLayer.L3_1_HOUR


if __name__ == "__main__":
    # 打印配置信息
    print("Clawra八层传播体系配置:")
    for layer, config in LAYER_CONFIGS.items():
        print(f"\n{layer.value}: {config.content_type}")
        print(f"  时长: {config.duration_seconds}秒 ({config.duration_seconds/3600:.1f}小时)")
        print(f"  情感强度: {config.emotional_intensity}")
        print(f"  认知负载: {config.cognitive_load}")
        print(f"  预估生产时间: {config.production_time_min}分钟")
