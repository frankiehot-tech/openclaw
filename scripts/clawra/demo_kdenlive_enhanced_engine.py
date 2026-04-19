#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra Kdenlive增强引擎演示脚本
展示如何使用Kdenlive增强引擎生成广告级视频
"""

import os
import sys
from pathlib import Path

# 添加路径以便导入
sys.path.append(str(Path(__file__).parent))

from video_generation.kdenlive_enhanced_engine import (
    KdenliveEnhancedVideoGenerationEngine,
)


def demo_ad_level_video_generation():
    """演示广告级视频生成"""
    print("=" * 60)
    print("🎬 Clawra Kdenlive增强引擎演示")
    print("=" * 60)

    # 创建引擎
    print("初始化Kdenlive增强引擎...")
    engine = KdenliveEnhancedVideoGenerationEngine(
        output_dir="./output/demo_videos", kdenlive_output_dir="./output/kdenlive_projects"
    )

    # 演示1: Open Human项目介绍视频
    print("\n" + "=" * 60)
    print("🎬 演示1: 生成Open Human项目介绍视频")
    print("=" * 60)

    success1, result1 = engine.generate_openhuman_intro_video()

    if success1:
        print(f"✅ 演示1成功!")
        print(f"   项目文件: {result1.get('project_file')}")
        print(f"   渲染命令: {result1.get('render_cmd', 'N/A')}")
        print(f"   文档文件: {result1.get('documentation', 'N/A')}")
    else:
        print(f"❌ 演示1失败: {result1.get('error', '未知错误')}")

    # 演示2: 自定义广告视频
    print("\n" + "=" * 60)
    print("🎬 演示2: 生成自定义社交广告")
    print("=" * 60)

    success2, result2 = engine.generate_ad_level_video(
        project_name="Demo_Social_Ad",
        resolution="social",  # 竖屏1080x1920
        fps="broadcast",  # 30fps
        duration_preset="social_short",  # 15秒
        content_template="product_showcase",
        title_text="新一代AI协作工具",
        product_text="智能任务分解、多模态内容生成、自动化工作流",
        call_to_action_text="立即体验，提升生产力",
    )

    if success2:
        print(f"✅ 演示2成功!")
        print(f"   项目文件: {result2.get('project_file')}")
        print(f"   渲染命令: {result2.get('render_cmd', 'N/A')}")
        print(f"   文档文件: {result2.get('documentation', 'N/A')}")
    else:
        print(f"❌ 演示2失败: {result2.get('error', '未知错误')}")

    # 演示3: GitHub项目发布视频
    print("\n" + "=" * 60)
    print("🎬 演示3: 生成GitHub项目发布视频")
    print("=" * 60)

    success3, result3 = engine.generate_github_project_announcement(
        repo_name="open-human", version="1.0.0"
    )

    if success3:
        print(f"✅ 演示3成功!")
        print(f"   项目文件: {result3.get('project_file')}")
        print(f"   渲染命令: {result3.get('render_cmd', 'N/A')}")
        print(f"   文档文件: {result3.get('documentation', 'N/A')}")
    else:
        print(f"❌ 演示3失败: {result3.get('error', '未知错误')}")

    # 演示总结
    print("\n" + "=" * 60)
    print("📊 演示总结")
    print("=" * 60)

    demos = [
        ("Open Human介绍视频", success1, result1),
        ("自定义社交广告", success2, result2),
        ("GitHub项目发布", success3, result3),
    ]

    total_demos = len(demos)
    successful_demos = sum(1 for _, success, _ in demos if success)

    print(f"演示总数: {total_demos}")
    print(f"成功: {successful_demos}")
    print(f"失败: {total_demos - successful_demos}")

    for name, success, result in demos:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
        if success:
            project_file = result.get("project_file", "N/A")
            if project_file != "N/A":
                print(f"    项目文件: {os.path.basename(project_file)}")

    print("\n" + "=" * 60)
    print("🎯 下一步操作建议")
    print("=" * 60)

    if successful_demos > 0:
        print("1. 📁 查看生成的项目文件:")
        for name, success, result in demos:
            if success and result.get("project_file"):
                print(f"   - {name}: {result['project_file']}")

        print("\n2. 🎬 渲染视频文件（使用melt）:")
        for name, success, result in demos:
            if success and result.get("render_cmd"):
                print(f"   - {name}:")
                print(f"     {result['render_cmd']}")

        print("\n3. 📄 查看项目文档:")
        for name, success, result in demos:
            if success and result.get("documentation"):
                print(f"   - {name}: {result['documentation']}")

        print("\n4. 🔧 在Kdenlive中编辑项目:")
        for name, success, result in demos:
            if success and result.get("project_file"):
                print(f"   - {name}: open {result['project_file']}")

    else:
        print("⚠️  所有演示均失败，请检查Kdenlive CLI配置和依赖")

    print("\n" + "=" * 60)
    print("✅ 演示完成!")
    print("=" * 60)

    return successful_demos > 0


def show_integration_guide():
    """显示集成指南"""
    print("\n" + "=" * 60)
    print("🔧 Clawra Kdenlive增强引擎集成指南")
    print("=" * 60)

    guide = """
## 如何将Kdenlive增强引擎集成到您的项目

### 1. 基础集成
```python
from video_generation.kdenlive_enhanced_engine import KdenliveEnhancedVideoGenerationEngine

# 创建引擎
engine = KdenliveEnhancedVideoGenerationEngine(
    output_dir="./videos",
    kdenlive_output_dir="./kdenlive_projects"
)

# 生成Open Human介绍视频
success, result = engine.generate_openhuman_intro_video()

# 生成自定义广告视频
success, result = engine.generate_ad_level_video(
    project_name="My_Ad_Campaign",
    resolution="standard",
    fps="broadcast",
    duration_preset="ad_standard",
    content_template="product_showcase",
    title_text="您的标题",
    product_text="产品描述",
    call_to_action_text="行动号召"
)

# 生成GitHub项目发布视频
success, result = engine.generate_github_project_announcement(
    repo_name="your-repo",
    version="1.0.0"
)
```

### 2. 与Athena/Clawra系统集成
```python
# 在Clawra主引擎中集成
class ClawraEnhancedSystem:
    def __init__(self):
        self.video_engine = KdenliveEnhancedVideoGenerationEngine()
        # ... 其他组件

    def generate_project_promo(self, project_info):
        '''为项目生成宣传视频'''
        if project_info.get('type') == 'github':
            return self.video_engine.generate_github_project_announcement(
                repo_name=project_info['repo'],
                version=project_info.get('version', '1.0.0')
            )
        elif project_info.get('type') == 'openhuman':
            return self.video_engine.generate_openhuman_intro_video()
        else:
            return self.video_engine.generate_ad_level_video(
                project_name=project_info.get('name', 'Project_Promo'),
                content_template="brand_story",
                title_text=project_info.get('title'),
                product_text=project_info.get('description')
            )
```

### 3. 自动化工作流示例
```python
# 自动化视频生成管道
def automated_video_pipeline(content_brief):
    '''基于内容简报自动生成视频'''
    engine = KdenliveEnhancedVideoGenerationEngine()

    # 分析内容类型
    if "开源" in content_brief or "GitHub" in content_brief:
        return engine.generate_github_project_announcement(
            extract_repo_name(content_brief),
            extract_version(content_brief)
        )
    elif "产品" in content_brief or "功能" in content_brief:
        return engine.generate_ad_level_video(
            content_template="product_showcase",
            title_text=extract_title(content_brief),
            product_text=extract_description(content_brief)
        )
    elif "品牌" in content_brief or "故事" in content_brief:
        return engine.generate_ad_level_video(
            content_template="brand_story",
            title_text=extract_brand_name(content_brief)
        )

    # 默认生成Open Human介绍
    return engine.generate_openhuman_intro_video()
```

### 4. 质量控制和验收标准
```python
# 视频质量检查
def validate_ad_video_quality(result):
    '''验证广告级视频质量'''
    checks = [
        ("✅ 项目文件存在", os.path.exists(result.get('project_file', ''))),
        ("✅ XML文件存在", os.path.exists(result.get('xml_file', ''))),
        ("✅ 文档已生成", os.path.exists(result.get('documentation', ''))),
        ("✅ 渲染命令有效", 'melt' in result.get('render_cmd', '')),
        ("✅ 分辨率符合标准", '1920x1080' in result.get('summary', '') or '1080x1920' in result.get('summary', '')),
        ("✅ 轨道配置正确", '轨道数:' in result.get('summary', '')),
    ]

    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")

    return all(check_result for _, check_result in checks)
```

### 5. 部署和生产建议
1. **环境要求**:
   - Python 3.8+
   - Kdenlive CLI (cli-anything/kdenlive)
   - melt (MLT框架，用于渲染)

2. **性能优化**:
   - 使用持久化输出目录避免重复创建
   - 配置Kdenlive项目模板提高效率
   - 实现视频渲染队列避免资源冲突

3. **监控和日志**:
   - 记录所有生成操作到数据库
   - 保存项目元数据和性能指标
   - 实现错误恢复和重试机制

4. **扩展性考虑**:
   - 支持自定义视频模板
   - 集成外部素材库（图片、音频、视频）
   - 添加多语言字幕支持
   - 实现批量视频生成
"""

    print(guide)


def main():
    """主函数"""
    print("🎬 Clawra Kdenlive增强视频生成系统")
    print("=" * 60)
    print("版本: 1.0.0 | 广告级视频生成引擎")
    print("项目: Athena/openclaw Clawra模块")
    print("=" * 60)

    # 运行演示
    demo_success = demo_ad_level_video_generation()

    # 显示集成指南
    show_integration_guide()

    # 退出状态
    if demo_success:
        print("\n✅ 演示成功完成!")
        print("Kdenlive增强引擎已准备好集成到Clawra系统。")
        return 0
    else:
        print("\n⚠️  演示部分失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
