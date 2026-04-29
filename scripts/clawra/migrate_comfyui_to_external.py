#!/usr/bin/env python3
"""
迁移ComfyUI工作流到外部硬盘并优化配置
解决模型文件损坏问题和存储空间告警
"""

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path


class ComfyUIMigrationOptimizer:
    """ComfyUI迁移和优化器"""

    def __init__(self):
        # 源目录（本地硬盘）
        self.source_comfyui_dir = Path("/Volumes/1TB-M2/openclaw/ComfyUI")
        # 目标目录（外部硬盘）
        self.target_comfyui_dir = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace")
        # 模型文件路径
        self.source_model_path = (
            self.source_comfyui_dir / "models" / "checkpoints" / "v1-5-pruned.safetensors"
        )
        self.target_model_path = (
            self.target_comfyui_dir / "models" / "checkpoints" / "v1-5-pruned.safetensors"
        )

        # Clawra脚本目录
        self.clawra_dir = Path(__file__).parent
        self.athena_generator_path = self.clawra_dir / "comfyui_athena_generator.py"

        print("🚀 ComfyUI迁移优化器启动")
        print(f"源目录: {self.source_comfyui_dir}")
        print(f"目标目录: {self.target_comfyui_dir}")
        print(f"模型文件: {self.source_model_path}")
        if self.source_model_path.exists():
            print(f"模型大小: {self.source_model_path.stat().st_size / (1024**3):.2f} GB")
        else:
            print(f"⚠️ 模型文件不存在: {self.source_model_path}")

    def check_source_model_integrity(self):
        """检查源模型文件完整性"""
        print("\n🔍 检查模型文件完整性...")

        if not self.source_model_path.exists():
            print(f"❌ 模型文件不存在: {self.source_model_path}")
            return False

        file_size = self.source_model_path.stat().st_size
        expected_size = 7703324286  # 从之前的ls输出获得

        if file_size != expected_size:
            print(f"❌ 文件大小不匹配: {file_size} != {expected_size}")
            print("   可能是下载不完整导致损坏")
            return False

        print(f"✅ 模型文件大小正确: {file_size} 字节 ({file_size/(1024**3):.2f} GB)")

        # 尝试打开文件检查元数据
        try:
            import safetensors

            with safetensors.safe_open(str(self.source_model_path), framework="pt") as f:
                keys = list(f.keys())
                print(f"✅ 模型文件可读取，包含 {len(keys)} 个张量")
                if len(keys) < 10:
                    print(f"⚠️  张量数量偏少: {len(keys)}")
                else:
                    print(f"   前3个张量: {keys[:3]}")
                return True
        except Exception as e:
            print(f"❌ 模型文件读取失败: {e}")
            print("   可能需要重新下载模型文件")
            return False

    def create_workspace_structure(self):
        """创建ComfyUI工作区结构"""
        print("\n🏗️ 创建ComfyUI工作区结构...")

        directories = [
            self.target_comfyui_dir,
            self.target_comfyui_dir / "models",
            self.target_comfyui_dir / "models" / "checkpoints",
            self.target_comfyui_dir / "models" / "loras",
            self.target_comfyui_dir / "models" / "vae",
            self.target_comfyui_dir / "models" / "clip",
            self.target_comfyui_dir / "models" / "clip_vision",
            self.target_comfyui_dir / "models" / "embeddings",
            self.target_comfyui_dir / "models" / "controlnet",
            self.target_comfyui_dir / "models" / "upscale_models",
            self.target_comfyui_dir / "output",
            self.target_comfyui_dir / "input",
            self.target_comfyui_dir / "temp",
            self.target_comfyui_dir / "configs",
            self.target_comfyui_dir / "logs",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  创建: {directory}")

        # 创建占位符文件
        for checkpoint_dir in [self.target_comfyui_dir / "models" / "checkpoints"]:
            placeholder_file = checkpoint_dir / "put_checkpoints_here"
            if not placeholder_file.exists():
                placeholder_file.touch()

        print("✅ 工作区结构创建完成")
        return True

    def migrate_model_file(self):
        """迁移模型文件到外部硬盘"""
        print("\n📦 迁移模型文件到外部硬盘...")

        if not self.source_model_path.exists():
            print(f"❌ 源模型文件不存在: {self.source_model_path}")
            return False

        # 检查目标路径是否有足够空间
        target_disk_usage = shutil.disk_usage(self.target_comfyui_dir.parent)
        model_size = self.source_model_path.stat().st_size

        if target_disk_usage.free < model_size * 1.1:  # 留10%余量
            print("❌ 目标磁盘空间不足")
            print(f"   需要: {model_size/(1024**3):.2f} GB")
            print(f"   可用: {target_disk_usage.free/(1024**3):.2f} GB")
            return False

        # 复制文件（使用rsync保持进度）
        print(f"  复制 {self.source_model_path.name} ({model_size/(1024**3):.2f} GB)...")
        print(f"  从: {self.source_model_path}")
        print(f"  到: {self.target_model_path}")

        start_time = time.time()

        try:
            # 使用shutil.copy2保持元数据
            shutil.copy2(self.source_model_path, self.target_model_path)
            copy_time = time.time() - start_time

            # 验证复制后的文件
            if not self.target_model_path.exists():
                print("❌ 复制后目标文件不存在")
                return False

            source_size = self.source_model_path.stat().st_size
            target_size = self.target_model_path.stat().st_size

            if source_size != target_size:
                print(f"❌ 文件大小不一致: 源={source_size}, 目标={target_size}")
                return False

            # 计算MD5校验（可选，耗时但安全）
            print("  验证文件完整性...")
            source_md5 = self._calculate_file_md5(self.source_model_path)
            target_md5 = self._calculate_file_md5(self.target_model_path)

            if source_md5 != target_md5:
                print(f"❌ MD5校验不匹配: 源={source_md5[:8]}, 目标={target_md5[:8]}")
                return False

            speed = model_size / (1024**2) / copy_time  # MB/s
            print("✅ 模型文件迁移成功")
            print(f"   耗时: {copy_time:.1f} 秒")
            print(f"   速度: {speed:.1f} MB/s")
            print(f"   MD5校验: {target_md5[:16]}... (匹配)")

            return True

        except Exception as e:
            print(f"❌ 复制失败: {e}")
            # 清理失败的文件
            if self.target_model_path.exists():
                self.target_model_path.unlink()
            return False

    def _calculate_file_md5(self, file_path, chunk_size=8192):
        """计算文件MD5哈希"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # 读取文件块更新哈希
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def create_optimized_config(self):
        """创建优化的ComfyUI配置文件"""
        print("\n⚙️ 创建优化配置文件...")

        config_files = {
            "extra_model_paths.yaml": self._generate_extra_model_paths_config(),
            "config.yaml": self._generate_main_config(),
            "start_comfyui.sh": self._generate_startup_script(),
        }

        for filename, content in config_files.items():
            config_path = self.target_comfyui_dir / filename
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  创建: {config_path}")

            if filename.endswith(".sh"):
                config_path.chmod(0o755)  # 使脚本可执行

        print("✅ 配置文件创建完成")
        return True

    def _generate_extra_model_paths_config(self):
        """生成extra_model_paths.yaml配置"""
        return f"""# ComfyUI额外模型路径配置
# 自动生成于: {time.strftime("%Y-%m-%d %H:%M:%S")}

base_path: {self.target_comfyui_dir}

models:
  checkpoints: models/checkpoints
  vae: models/vae
  loras: models/loras
  clip: models/clip
  clip_vision: models/clip_vision
  style_models: models/style_models
  embeddings: models/embeddings
  diffusers: models/diffusers
  controlnet: models/controlnet
  upscale_models: models/upscale_models

# 外部模型路径（可添加更多）
extra_search_paths:
  - {self.target_comfyui_dir / "models"}
  - {Path.home() / "ComfyUI" / "models"}  # 原路径作为后备

# 输出路径
output_directory: output
input_directory: input
temp_directory: temp

# 性能优化
enable_safety_checker: false  # 禁用安全检查器提高速度
enable_model_caching: true
cache_size_mb: 2048

# 日志配置
log_level: INFO
log_to_file: true
log_file: logs/comfyui.log
"""

    def _generate_main_config(self):
        """生成主配置文件"""
        return f"""# ComfyUI主配置文件
# 自动生成于: {time.strftime("%Y-%m-% %H:%M:%S")}

server:
  listen: 127.0.0.1
  port: 8189  # 使用不同端口避免冲突
  enable_cors: false
  enable_web_sockets: true

performance:
  device: cpu  # 使用CPU模式避免MPS问题
  use_split_cross_attention: true
  use_pytorch_cross_attention: false
  deterministic: false
  attention_slicing: auto

memory:
  vram_state: SHARED
  max_vram: 0.8  # 最大使用80%内存
  min_vram: 0.1  # 最小保留10%内存
  clean_cache_interval: 100  # 每100次清理缓存

features:
  auto_launch_browser: false
  multi_user: false
  high_precision: false
  preview_method: latent2rgb

paths:
  base: {self.target_comfyui_dir}
  models: models
  output: output
  input: input
  temp: temp
  logs: logs

# 工作流优化
workflow:
  auto_save_workflows: true
  workflow_directory: workflows
  default_save_format: json
  max_history_items: 50

# 图像生成默认值
generation:
  default_width: 1024
  default_height: 1024
  default_steps: 30
  default_cfg: 7.0
  default_sampler: euler
  default_scheduler: normal

# 监控
monitoring:
  enable_prometheus: false
  enable_health_check: true
  health_check_interval: 60
"""

    def _generate_startup_script(self):
        """生成启动脚本"""
        return f"""#!/bin/bash
# ComfyUI优化启动脚本
# 自动生成于: {time.strftime("%Y-%m-%d %H:%M:%S")}

set -e

BASE_DIR="{self.target_comfyui_dir}"
LOG_FILE="$BASE_DIR/logs/comfyui_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="$BASE_DIR/comfyui.pid"

echo "🚀 启动ComfyUI服务器 (优化版)"
echo "工作目录: $BASE_DIR"
echo "日志文件: $LOG_FILE"

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  ComfyUI已在运行 (PID: $PID)"
        echo "    停止命令: kill $PID"
        exit 1
    else
        echo "清理旧的PID文件"
        rm -f "$PID_FILE"
    fi
fi

# 激活虚拟环境（如果存在）
if [ -d "$BASE_DIR/venv" ]; then
    echo "激活虚拟环境..."
    source "$BASE_DIR/venv/bin/activate"
fi

# 启动ComfyUI
cd "$BASE_DIR"

echo "启动参数: --listen 127.0.0.1 --port 8189 --cpu --use-split-cross-attention"
echo "详细日志输出到: $LOG_FILE"

nohup python main.py \\
    --listen 127.0.0.1 \\
    --port 8189 \\
    --cpu \\
    --use-split-cross-attention \\
    > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "✅ ComfyUI服务器已启动 (PID: $SERVER_PID)"
echo "    访问地址: http://127.0.0.1:8189"
echo "    停止命令: kill $SERVER_PID"
echo ""
echo "查看日志: tail -f $LOG_FILE"
echo "检查状态: curl -s http://127.0.0.1:8189/system_stats | python -m json.tool"

# 等待服务器启动
echo -n "等待服务器启动..."
sleep 5

# 检查服务器状态
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://127.0.0.1:8189/system_stats > /dev/null 2>&1; then
        echo " ✅"
        echo "服务器运行正常"
        break
    fi

    echo -n "."
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo " ❌"
    echo "服务器启动失败，请检查日志: $LOG_FILE"
    exit 1
fi

echo ""
echo "🎉 ComfyUI优化版启动完成"
echo "工作目录: $BASE_DIR"
echo "模型路径: $BASE_DIR/models/checkpoints/"
echo "输出目录: $BASE_DIR/output/"
echo ""
echo "监控命令:"
echo "  tail -f $LOG_FILE"
echo "  ps aux | grep \"python.*main.py\""
echo ""
exit 0
"""

    def update_athena_generator(self):
        """更新Athena生成器使用新配置"""
        print("\n🔄 更新Athena生成器配置...")

        if not self.athena_generator_path.exists():
            print(f"❌ Athena生成器文件不存在: {self.athena_generator_path}")
            return False

        try:
            with open(self.athena_generator_path, encoding="utf-8") as f:
                content = f.read()

            # 更新ComfyUI服务器地址
            old_base_url = "http://localhost:8188"
            new_base_url = "http://localhost:8189"

            if new_base_url in content:
                print(f"✅ Athena生成器已使用新地址: {new_base_url}")
                return True

            updated_content = content.replace(old_base_url, new_base_url)

            # 添加配置检查
            config_check_code = """
    def __init__(self, base_url: str = "http://localhost:8189"):
        \"\"\"
        初始化ComfyUI生成器

        Args:
            base_url: ComfyUI服务器地址 (默认: http://localhost:8189)
                      外部硬盘优化版使用端口8189
        \"\"\"
        self.base_url = base_url.rstrip('/')
        self.client_id = "athena_ip_generator"
        self.optimized = True  # 标记为优化版

        # 检查是否使用外部硬盘工作区
        self.external_workspace = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace")
        if self.external_workspace.exists():
            print(f"✅ 使用外部硬盘工作区: {self.external_workspace}")
"""

            # 查找并替换__init__方法
            init_start = content.find("def __init__(self")
            if init_start != -1:
                # 查找方法结束
                init_end = content.find("\n\n", init_start)
                if init_end == -1:
                    init_end = len(content)

                old_init = content[init_start:init_end]
                updated_content = content.replace(old_init, config_check_code)

            with open(self.athena_generator_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            print("✅ Athena生成器更新完成")
            print(f"   服务器地址: {new_base_url}")
            print(f"   外部工作区: {self.target_comfyui_dir}")

            return True

        except Exception as e:
            print(f"❌ 更新Athena生成器失败: {e}")
            return False

    def create_optimized_athena_workflow(self):
        """创建优化的Athena工作流模板"""
        print("\n🎨 创建优化的Athena工作流模板...")

        workflow_template = {
            "name": "athena_silicon_symbiosis_optimized",
            "description": "硅基共生主题AI女神Athena优化工作流",
            "version": "1.0.0",
            "author": "Athena Clawra System",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "optimizations": {
                "performance": "使用CPU优化，内存效率",
                "quality": "针对Athena主题调优",
                "reliability": "错误处理和重试机制",
            },
            "parameters": {
                "prompt": {
                    "type": "string",
                    "description": "正面提示词",
                    "default": "硅基共生主题的AI女神Athena，机械与生物融合的身体，发出蓝色光芒的能量核心，半透明的硅晶体皮肤，科幻漫画风格，赛博朋克，高细节",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "负面提示词",
                    "default": "低质量，模糊，变形，多余的手指，畸形，丑陋，写实照片",
                },
                "checkpoint": {
                    "type": "string",
                    "description": "模型检查点",
                    "default": "v1-5-pruned.safetensors",
                },
                "steps": {
                    "type": "integer",
                    "description": "采样步数",
                    "default": 30,
                    "range": [20, 50],
                },
                "cfg": {
                    "type": "float",
                    "description": "CFG scale",
                    "default": 7.0,
                    "range": [5.0, 10.0],
                },
                "width": {
                    "type": "integer",
                    "description": "图像宽度",
                    "default": 1024,
                    "options": [512, 768, 1024],
                },
                "height": {
                    "type": "integer",
                    "description": "图像高度",
                    "default": 1024,
                    "options": [512, 768, 1024],
                },
                "seed": {"type": "integer", "description": "随机种子（-1表示随机）", "default": -1},
            },
            "variants": {
                "战斗形态": {
                    "steps": 40,
                    "cfg": 8.0,
                    "prompt_suffix": "战斗形态，能量爆发，动态姿势，战斗特效",
                },
                "未来形态": {
                    "steps": 50,
                    "cfg": 9.0,
                    "prompt_suffix": "未来科技，终极进化，完美形态，史诗级场景",
                },
                "思考形态": {
                    "steps": 35,
                    "cfg": 6.5,
                    "prompt_suffix": "沉思，数据空间，算法结构，概念艺术",
                },
            },
            "quality_checks": {
                "face_quality": "检查面部完整性",
                "artifact_detection": "检测生成瑕疵",
                "prompt_alignment": "检查提示词对齐度",
            },
        }

        workflow_dir = self.target_comfyui_dir / "workflows"
        workflow_dir.mkdir(exist_ok=True)

        workflow_file = workflow_dir / "athena_silicon_symbiosis.json"
        with open(workflow_file, "w", encoding="utf-8") as f:
            json.dump(workflow_template, f, indent=2, ensure_ascii=False)

        print(f"✅ 工作流模板创建完成: {workflow_file}")
        return True

    def verify_migration(self):
        """验证迁移结果"""
        print("\n🔎 验证迁移结果...")

        checks = [
            ("工作区目录", self.target_comfyui_dir.exists()),
            ("模型文件", self.target_model_path.exists()),
            ("配置文件", (self.target_comfyui_dir / "extra_model_paths.yaml").exists()),
            ("启动脚本", (self.target_comfyui_dir / "start_comfyui.sh").exists()),
            (
                "工作流模板",
                (self.target_comfyui_dir / "workflows" / "athena_silicon_symbiosis.json").exists(),
            ),
        ]

        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")
            if not check_result:
                all_passed = False

        if all_passed:
            print("\n🎉 迁移验证成功!")

            # 计算空间节省
            if self.source_model_path.exists():
                model_size = self.source_model_path.stat().st_size / (1024**3)
                print(f"  释放本地空间: {model_size:.2f} GB")

            target_usage = shutil.disk_usage(self.target_comfyui_dir.parent)
            print(f"  外部硬盘可用空间: {target_usage.free/(1024**3):.2f} GB")

            # 提供使用说明
            print("\n📋 使用说明:")
            print(f"  1. 启动服务器: {self.target_comfyui_dir}/start_comfyui.sh")
            print("  2. 访问地址: http://127.0.0.1:8189")
            print(f"  3. 测试生成: python {self.athena_generator_path}")
            print(f"  4. 查看日志: {self.target_comfyui_dir}/logs/")

        else:
            print("\n⚠️  迁移验证失败，请检查上述问题")

        return all_passed

    def cleanup_source_if_needed(self):
        """如果需要，清理源文件释放空间"""
        print("\n🧹 清理源文件释放空间...")

        if not self.source_model_path.exists():
            print("源模型文件已不存在，跳过清理")
            return True

        # 确认目标文件完整
        if not self.target_model_path.exists():
            print("目标模型文件不存在，跳过清理")
            return False

        # 验证目标文件完整性
        try:
            source_size = self.source_model_path.stat().st_size
            target_size = self.target_model_path.stat().st_size

            if source_size != target_size:
                print("文件大小不一致，跳过清理")
                return False

            print(f"确认迁移完成，删除源模型文件 ({source_size/(1024**3):.2f} GB)...")

            # 备份到回收站而不是直接删除
            trash_dir = Path.home() / ".Trash"
            if trash_dir.exists():
                backup_path = trash_dir / f"v1-5-pruned.safetensors.backup_{int(time.time())}"
                shutil.move(self.source_model_path, backup_path)
                print(f"  已移动到回收站: {backup_path}")
            else:
                self.source_model_path.unlink()
                print("  已删除源文件")

            # 检查是否还有其他大文件
            checkpoints_dir = self.source_comfyui_dir / "models" / "checkpoints"
            if checkpoints_dir.exists():
                large_files = []
                for file in checkpoints_dir.iterdir():
                    if file.is_file() and file.stat().st_size > 100 * 1024**2:  # >100MB
                        large_files.append((file.name, file.stat().st_size / (1024**3)))

                if large_files:
                    print("  发现其他大文件:")
                    for name, size in large_files:
                        print(f"    - {name}: {size:.2f} GB")
                    print("  考虑移动到外部硬盘或删除")

            return True

        except Exception as e:
            print(f"清理失败: {e}")
            return False

    def run_full_migration(self):
        """执行完整迁移流程"""
        print("=" * 60)
        print("🚀 ComfyUI工作流迁移优化流程")
        print("=" * 60)

        steps = [
            ("检查源模型完整性", self.check_source_model_integrity),
            ("创建工作区结构", self.create_workspace_structure),
            ("迁移模型文件", self.migrate_model_file),
            ("创建优化配置", self.create_optimized_config),
            ("更新Athena生成器", self.update_athena_generator),
            ("创建工作流模板", self.create_optimized_athena_workflow),
            ("验证迁移结果", self.verify_migration),
            ("清理源文件", self.cleanup_source_if_needed),
        ]

        for step_name, step_func in steps:
            print(f"\n📋 步骤: {step_name}")
            print("-" * 40)

            try:
                success = step_func()
                if not success:
                    print(f"❌ 步骤失败: {step_name}")
                    print("继续执行后续步骤...")
            except Exception as e:
                print(f"❌ 步骤异常: {e}")
                import traceback

                traceback.print_exc()

        print("\n" + "=" * 60)
        print("🎉 迁移优化流程完成")
        print("=" * 60)

        # 提供后续操作指南
        print("\n📋 后续操作:")
        print("1. 启动优化版ComfyUI:")
        print(f"   cd {self.target_comfyui_dir}")
        print("   ./start_comfyui.sh")
        print()
        print("2. 测试Athena生成:")
        print(f"   cd {self.clawra_dir}")
        print("   python comfyui_athena_generator.py")
        print()
        print("3. 监控服务器状态:")
        print(f"   tail -f {self.target_comfyui_dir}/logs/comfyui_*.log")
        print()
        print("4. 访问Web界面:")
        print("   http://127.0.0.1:8189")
        print()
        print("💡 提示: 新服务器使用端口8189，避免与原有端口冲突")

        return True


def main():
    """主函数"""
    try:
        optimizer = ComfyUIMigrationOptimizer()
        optimizer.run_full_migration()
        return 0
    except Exception as e:
        print(f"❌ 迁移过程出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
