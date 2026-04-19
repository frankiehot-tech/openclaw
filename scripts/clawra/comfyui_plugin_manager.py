#!/usr/bin/env python3
"""
ComfyUI插件管理器
管理ComfyUI插件的安装、配置和集成
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ComfyUI目录配置
COMFYUI_BASE_DIR = Path("/Users/frankie/ComfyUI")
COMFYUI_CUSTOM_NODES_DIR = COMFYUI_BASE_DIR / "custom_nodes"
EXTERNAL_WORKSPACE_DIR = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace")


@dataclass
class PluginInfo:
    """插件信息"""

    name: str
    description: str
    repo_url: Optional[str] = None
    repo_path: Optional[str] = None  # 本地路径
    version: str = "1.0.0"
    node_types: List[str] = None
    dependencies: List[str] = None
    installed: bool = False
    enabled: bool = True

    def __post_init__(self):
        if self.node_types is None:
            self.node_types = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class WorkflowTemplate:
    """工作流模板"""

    name: str
    description: str
    workflow_json: Dict[str, Any]
    required_plugins: List[str]
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ComfyUIPluginManager:
    """ComfyUI插件管理器"""

    def __init__(self, comfyui_base_dir: Path = None):
        self.base_dir = comfyui_base_dir or COMFYUI_BASE_DIR
        self.custom_nodes_dir = self.base_dir / "custom_nodes"
        self.workspace_dir = EXTERNAL_WORKSPACE_DIR
        self.plugins_config_file = self.workspace_dir / "plugins_config.json"

        # 确保目录存在
        self.custom_nodes_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # 加载插件配置
        self.plugins = self._load_plugins_config()

        # 预定义的核心插件
        self._define_core_plugins()

    def _load_plugins_config(self) -> Dict[str, PluginInfo]:
        """加载插件配置"""
        if self.plugins_config_file.exists():
            try:
                with open(self.plugins_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                plugins = {}
                for name, plugin_data in data.items():
                    plugin = PluginInfo(**plugin_data)
                    plugins[name] = plugin
                return plugins
            except Exception as e:
                print(f"[WARN] 加载插件配置失败: {e}")
                return {}
        return {}

    def _save_plugins_config(self):
        """保存插件配置"""
        try:
            data = {name: asdict(plugin) for name, plugin in self.plugins.items()}
            with open(self.plugins_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] 保存插件配置失败: {e}")

    def _define_core_plugins(self):
        """定义核心插件（基于搜索结果）"""
        core_plugins = {
            "comfyui_panels": PluginInfo(
                name="comfyui_panels",
                description="漫画/漫画类似的面板布局插件，支持多面板生成",
                repo_url="https://github.com/bmad4ever/comfyui_panels",
                node_types=["PanelLayout", "ComicPageGenerator", "PanelSplitter"],
                dependencies=["git", "python3"],
                installed=False,
                enabled=True,
            ),
            "ltx2_3_workflow": PluginInfo(
                name="ltx2_3_workflow",
                description="LTX2.3 20宫格工作流，一句话到1分钟AI漫剧",
                repo_url="",  # 需要从多个来源获取
                node_types=["LTX23Workflow", "StoryBoardGenerator", "VideoComposer"],
                dependencies=["git", "python3", "ffmpeg"],
                installed=False,
                enabled=True,
            ),
            "athena_ip_generator": PluginInfo(
                name="athena_ip_generator",
                description="Athena IP形象生成器，集成到Clawra系统",
                repo_path=str(Path(__file__).parent / "comfyui_athena_generator.py"),
                node_types=["AthenaImageGenerator", "AthenaStyleTransfer"],
                dependencies=[],
                installed=True,  # 已作为本地模块存在
                enabled=True,
            ),
        }

        # 更新或添加核心插件
        for name, plugin in core_plugins.items():
            if name not in self.plugins:
                self.plugins[name] = plugin

    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self.plugins.values())

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugins.get(name)

    def install_plugin(self, plugin_name: str, force_reinstall: bool = False) -> bool:
        """安装插件"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"[ERROR] 插件不存在: {plugin_name}")
            return False

        if plugin.installed and not force_reinstall:
            print(f"[INFO] 插件已安装: {plugin_name}")
            return True

        print(f"[INFO] 开始安装插件: {plugin_name}")

        try:
            if plugin.repo_url and plugin.repo_url.startswith("http"):
                # Git仓库安装
                return self._install_from_git(plugin)
            elif plugin.repo_path:
                # 本地路径安装
                return self._install_from_local(plugin)
            else:
                print(f"[ERROR] 无有效的安装源: {plugin_name}")
                return False
        except Exception as e:
            print(f"[ERROR] 安装插件失败 {plugin_name}: {e}")
            return False

    def _install_from_git(self, plugin: PluginInfo) -> bool:
        """从Git仓库安装"""
        try:
            # 克隆或更新仓库
            plugin_dir = self.custom_nodes_dir / plugin.name

            if plugin_dir.exists():
                print(f"[INFO] 更新现有插件: {plugin.name}")
                subprocess.run(["git", "pull"], cwd=plugin_dir, check=True)
            else:
                print(f"[INFO] 克隆插件仓库: {plugin.repo_url}")
                subprocess.run(["git", "clone", plugin.repo_url, str(plugin_dir)], check=True)

            # 检查requirements.txt
            requirements_file = plugin_dir / "requirements.txt"
            if requirements_file.exists():
                print(f"[INFO] 安装Python依赖")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    check=True,
                )

            plugin.installed = True
            self._save_plugins_config()
            print(f"[SUCCESS] 插件安装成功: {plugin.name}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Git操作失败: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] 安装失败: {e}")
            return False

    def _install_from_local(self, plugin: PluginInfo) -> bool:
        """从本地路径安装"""
        try:
            source_path = Path(plugin.repo_path)
            if not source_path.exists():
                print(f"[ERROR] 本地路径不存在: {source_path}")
                return False

            # 如果是Python模块，复制到custom_nodes目录
            target_dir = self.custom_nodes_dir / plugin.name
            target_dir.mkdir(parents=True, exist_ok=True)

            if source_path.is_file():
                # 单个文件
                shutil.copy2(source_path, target_dir / source_path.name)
            elif source_path.is_dir():
                # 整个目录
                # 先删除目标目录（如果存在）
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(source_path, target_dir)

            plugin.installed = True
            self._save_plugins_config()
            print(f"[SUCCESS] 本地插件安装成功: {plugin.name}")
            return True

        except Exception as e:
            print(f"[ERROR] 本地安装失败: {e}")
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"[ERROR] 插件不存在: {plugin_name}")
            return False

        if not plugin.installed:
            print(f"[INFO] 插件未安装: {plugin_name}")
            return True

        try:
            plugin_dir = self.custom_nodes_dir / plugin.name
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
                print(f"[INFO] 删除插件目录: {plugin_dir}")

            plugin.installed = False
            self._save_plugins_config()
            print(f"[SUCCESS] 插件卸载成功: {plugin_name}")
            return True

        except Exception as e:
            print(f"[ERROR] 卸载失败: {e}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"[ERROR] 插件不存在: {plugin_name}")
            return False

        plugin.enabled = True
        self._save_plugins_config()
        print(f"[INFO] 插件已启用: {plugin_name}")
        return True

    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"[ERROR] 插件不存在: {plugin_name}")
            return False

        plugin.enabled = False
        self._save_plugins_config()
        print(f"[INFO] 插件已禁用: {plugin_name}")
        return True

    def check_compatibility(self, plugin_name: str) -> Dict[str, Any]:
        """检查插件兼容性"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {"error": f"插件不存在: {plugin_name}"}

        result = {
            "plugin": plugin.name,
            "installed": plugin.installed,
            "enabled": plugin.enabled,
            "compatibility_issues": [],
        }

        # 检查依赖
        for dep in plugin.dependencies:
            try:
                if dep == "git":
                    subprocess.run(["git", "--version"], capture_output=True, check=True)
                elif dep == "python3":
                    subprocess.run(["python3", "--version"], capture_output=True, check=True)
                elif dep == "ffmpeg":
                    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                result["compatibility_issues"].append(f"依赖缺失: {dep}")

        # 检查节点类型是否已注册（需要重启ComfyUI后检查）

        return result

    def restart_comfyui_needed(self) -> bool:
        """检查是否需要重启ComfyUI"""
        # 如果有插件安装/卸载/启用/禁用操作，需要重启
        # 简化实现：总是返回True，需要用户手动重启
        return True

    def create_workflow_template(self, template_name: str) -> Optional[WorkflowTemplate]:
        """创建工作流模板"""
        templates = {
            "athena_portrait": WorkflowTemplate(
                name="athena_portrait",
                description="Athena人物肖像生成工作流",
                workflow_json=self._create_athena_portrait_workflow(),
                required_plugins=["athena_ip_generator"],
                tags=["athena", "portrait", "character"],
            ),
            "comic_panels_basic": WorkflowTemplate(
                name="comic_panels_basic",
                description="基础漫画面板生成工作流",
                workflow_json=self._create_comic_panels_workflow(),
                required_plugins=["comfyui_panels"],
                tags=["comic", "panels", "manga"],
            ),
            "ltx23_storyboard": WorkflowTemplate(
                name="ltx23_storyboard",
                description="LTX2.3故事板生成工作流",
                workflow_json=self._create_ltx23_storyboard_workflow(),
                required_plugins=["ltx2_3_workflow"],
                tags=["ltx23", "storyboard", "video", "comic"],
            ),
        }

        return templates.get(template_name)

    def _create_athena_portrait_workflow(self) -> Dict[str, Any]:
        """创建Athena肖像工作流"""
        # 使用现有的comfyui_athena_generator工作流结构
        return {
            "0e31e40d_checkpoint": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned.safetensors"},
            },
            "0e31e40d_positive": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "硅基共生主题的AI女神Athena,机械与生物融合的身体,发出蓝色光芒的能量核心,半透明的硅晶体皮肤,未来科技感,赛博朋克风格,精致的机械细节,发光电路纹理,生物机械共生体,美丽而强大的女性形象,银色和蓝色配色,动态光效,科幻漫画风格,高细节,大师级作品",
                    "clip": ["0e31e40d_checkpoint", 1],
                },
            },
            "0e31e40d_negative": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "低质量,模糊,变形,多余的手指,畸形,丑陋,写实照片",
                    "clip": ["0e31e40d_checkpoint", 1],
                },
            },
            "0e31e40d_empty_latent": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
            },
            "0e31e40d_ksampler": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 3827960399,
                    "steps": 50,
                    "cfg": 9.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["0e31e40d_checkpoint", 0],
                    "positive": ["0e31e40d_positive", 0],
                    "negative": ["0e31e40d_negative", 0],
                    "latent_image": ["0e31e40d_empty_latent", 0],
                },
            },
            "0e31e40d_vae": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["0e31e40d_ksampler", 0], "vae": ["0e31e40d_checkpoint", 2]},
            },
            "0e31e40d_save": {
                "class_type": "SaveImage",
                "inputs": {"images": ["0e31e40d_vae", 0], "filename_prefix": "athena_portrait"},
            },
        }

    def _create_comic_panels_workflow(self) -> Dict[str, Any]:
        """创建漫画面板工作流（占位符）"""
        # 实际工作流需要根据comfyui_panels插件的节点类型调整
        return {
            "note": "这是comic_panels工作流的占位符。需要安装comfyui_panels插件后获取实际的节点结构。",
            "workflow_type": "comic_panels",
            "status": "placeholder",
        }

    def _create_ltx23_storyboard_workflow(self) -> Dict[str, Any]:
        """创建LTX2.3故事板工作流（占位符）"""
        # 实际工作流需要根据LTX2.3工作流的节点类型调整
        return {
            "note": "这是LTX2.3故事板工作流的占位符。需要获取实际的工作流JSON后更新。",
            "workflow_type": "ltx23_storyboard",
            "status": "placeholder",
        }

    def save_workflow(self, template: WorkflowTemplate, output_path: Path) -> bool:
        """保存工作流到文件"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(template.workflow_json, f, indent=2, ensure_ascii=False)
            print(f"[SUCCESS] 工作流保存到: {output_path}")
            return True
        except Exception as e:
            print(f"[ERROR] 保存工作流失败: {e}")
            return False


def main():
    """主函数"""
    print("🎨 ComfyUI插件管理器")
    print("=" * 60)

    manager = ComfyUIPluginManager()

    # 列出所有插件
    plugins = manager.list_plugins()
    print(f"📦 可用插件 ({len(plugins)}):")
    for plugin in plugins:
        status = "✅" if plugin.installed else "❌"
        enabled = "🟢" if plugin.enabled else "🔴"
        print(f"  {status}{enabled} {plugin.name}: {plugin.description}")
        if plugin.installed:
            print(f"     节点类型: {', '.join(plugin.node_types)}")

    print("\n" + "=" * 60)

    # 检查核心插件状态
    core_plugins = ["comfyui_panels", "ltx2_3_workflow", "athena_ip_generator"]
    for plugin_name in core_plugins:
        compat = manager.check_compatibility(plugin_name)
        print(f"🔍 {plugin_name} 兼容性检查:")
        print(f"   已安装: {compat.get('installed', False)}")
        print(f"   已启用: {compat.get('enabled', False)}")
        issues = compat.get("compatibility_issues", [])
        if issues:
            print(f"   问题: {', '.join(issues)}")
        else:
            print(f"   ✅ 无兼容性问题")

    print("\n" + "=" * 60)
    print("💡 使用示例:")
    print("  1. 安装插件: manager.install_plugin('comfyui_panels')")
    print("  2. 创建工作流: manager.create_workflow_template('comic_panels_basic')")
    print("  3. 检查兼容性: manager.check_compatibility('ltx2_3_workflow')")
    print("\n⚠️  注意: 安装插件后需要重启ComfyUI服务器")

    return 0


if __name__ == "__main__":
    sys.exit(main())
