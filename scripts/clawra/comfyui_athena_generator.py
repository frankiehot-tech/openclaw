#!/usr/bin/env python3
"""
Athena IP形象ComfyUI生成器
基于ComfyUI API的Athena图像生成系统
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.append(str(Path(__file__).parent))


@dataclass
class ComfyUIGenerationResult:
    """ComfyUI生成结果"""

    image_path: str
    prompt_id: str
    node_id: str
    workflow: Dict[str, Any]
    metadata: Dict[str, Any]


class ComfyUIAthenaGenerator:
    """Athena IP形象ComfyUI生成器"""

    def __init__(self, base_url: str = "http://localhost:8189"):
        """
        初始化ComfyUI生成器

        Args:
            base_url: ComfyUI服务器地址 (默认: http://localhost:8189)
                      外部硬盘优化版使用端口8189
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = "athena_ip_generator"
        self.optimized = True  # 标记为优化版

        # 检查是否使用外部硬盘工作区
        self.external_workspace = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace")
        if self.external_workspace.exists():
            print(f"[OK] 使用外部硬盘工作区: {self.external_workspace}")

    def check_server_status(self) -> bool:
        """检查ComfyUI服务器状态"""
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] ComfyUI服务器连接失败: {e}")
            print(f"   请确保ComfyUI正在运行: {self.base_url}")
            return False

    def create_athena_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        checkpoint: str = "v1-5-pruned.safetensors",
        steps: int = 30,
        cfg: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        seed: int = -1,
    ) -> Dict[str, Any]:
        """
        创建Athena IP形象专用工作流

        Args:
            prompt: 正面提示词
            negative_prompt: 负面提示词
            checkpoint: 模型检查点名称
            steps: 采样步数
            cfg: CFG scale
            width: 图像宽度
            height: 图像高度
            seed: 随机种子 (-1表示随机)

        Returns:
            ComfyUI工作流JSON
        """
        # 生成随机节点ID（避免冲突）
        import hashlib
        import time

        timestamp = int(time.time() * 1000)
        base_id = hashlib.md5(f"{timestamp}{prompt[:20]}".encode()).hexdigest()[:8]

        node_ids = {
            "checkpoint": f"{base_id}_checkpoint",
            "positive": f"{base_id}_positive",
            "negative": f"{base_id}_negative",
            "empty_latent": f"{base_id}_empty_latent",
            "ksampler": f"{base_id}_ksampler",
            "vae": f"{base_id}_vae",
            "save": f"{base_id}_save",
        }

        # 处理随机种子
        import random

        actual_seed = seed if seed >= 0 else random.randint(0, 2**32 - 1)

        # 基础工作流结构
        workflow = {
            node_ids["checkpoint"]: {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            node_ids["positive"]: {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": [node_ids["checkpoint"], 1],  # checkpoint的CLIP输出
                },
            },
            node_ids["negative"]: {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": [node_ids["checkpoint"], 1],  # checkpoint的CLIP输出
                },
            },
            node_ids["empty_latent"]: {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            node_ids["ksampler"]: {
                "class_type": "KSampler",
                "inputs": {
                    "seed": actual_seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": [node_ids["checkpoint"], 0],  # checkpoint的模型输出
                    "positive": [node_ids["positive"], 0],
                    "negative": [node_ids["negative"], 0],
                    "latent_image": [node_ids["empty_latent"], 0],
                },
            },
            node_ids["vae"]: {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": [node_ids["ksampler"], 0],
                    "vae": [node_ids["checkpoint"], 2],  # checkpoint的VAE输出
                },
            },
            node_ids["save"]: {
                "class_type": "SaveImage",
                "inputs": {
                    "images": [node_ids["vae"], 0],
                    "filename_prefix": f"athena_{timestamp}",
                },
            },
        }

        return workflow

    def queue_prompt(self, workflow: Dict[str, Any]) -> Optional[str]:
        """
        提交工作流到ComfyUI队列

        Args:
            workflow: ComfyUI工作流

        Returns:
            prompt_id: 提示ID (用于追踪)
        """
        try:
            payload = {"prompt": workflow, "client_id": self.client_id}

            response = requests.post(f"{self.base_url}/prompt", json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                print(f"[OK] 工作流已提交,Prompt ID: {prompt_id}")
                return prompt_id
            else:
                print(f"[ERROR] 提交失败: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"[ERROR] 提交工作流出错: {e}")
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        try:
            response = requests.get(f"{self.base_url}/queue", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"状态码: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> bool:
        """
        等待生成完成

        Args:
            prompt_id: 提示ID
            timeout: 超时时间(秒)

        Returns:
            是否成功完成
        """
        print(f"⏳ 等待生成完成 (超时: {timeout}秒)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 检查历史记录
            try:
                response = requests.get(f"{self.base_url}/history", timeout=10)
                if response.status_code == 200:
                    history = response.json()

                    # 检查我们的prompt_id是否在已完成列表中
                    if prompt_id in history:
                        print(f"[OK] 生成完成: {prompt_id}")
                        return True

                    # 检查当前队列
                    queue_status = self.get_queue_status()

                    # 处理可能的错误响应
                    if isinstance(queue_status, dict):
                        queue_running = queue_status.get("queue_running", [])
                        queue_pending = queue_status.get("queue_pending", [])

                        # 确保queue_running和queue_pending是列表
                        if not isinstance(queue_running, list):
                            queue_running = []
                        if not isinstance(queue_pending, list):
                            queue_pending = []

                        # 如果不在运行中也不在等待中,可能已完成或失败
                        in_queue = False
                        for item in queue_running + queue_pending:
                            if isinstance(item, list) and len(item) > 1 and item[1] == prompt_id:
                                in_queue = True
                                break
                            elif isinstance(item, dict) and item.get("prompt_id") == prompt_id:
                                in_queue = True
                                break

                        if not in_queue:
                            print(f"[WARN]  Prompt ID {prompt_id} 不在队列中")
                            return False
                    else:
                        # queue_status不是字典,可能是错误信息
                        print(f"[WARN]  队列状态异常: {queue_status}")
                        # 继续等待

                time.sleep(2)  # 等待2秒再检查

            except Exception as e:
                print(f"[ERROR] 检查状态出错: {e}")
                time.sleep(5)

        print(f"[ERROR] 等待超时: {timeout}秒")
        return False

    def get_generated_images(self, prompt_id: str) -> List[Dict[str, str]]:
        """
        获取生成的图像

        Args:
            prompt_id: 提示ID

        Returns:
            图像信息列表
        """
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                images = []

                for node_id, node_output in result.get(prompt_id, {}).get("outputs", {}).items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            images.append(
                                {
                                    "node_id": node_id,
                                    "filename": image_info.get("filename"),
                                    "subfolder": image_info.get("subfolder", ""),
                                    "type": image_info.get("type", "output"),
                                }
                            )

                return images
            else:
                print(f"[ERROR] 获取图像失败: {response.status_code}")
                return []

        except Exception as e:
            print(f"[ERROR] 获取图像出错: {e}")
            return []

    def download_image(
        self, filename: str, subfolder: str = "", output_path: str = "./generated"
    ) -> Optional[str]:
        """
        下载生成的图像

        Args:
            filename: 文件名
            subfolder: 子文件夹
            output_path: 本地保存路径

        Returns:
            本地文件路径
        """
        try:
            # 构建图像URL
            if subfolder:
                image_url = f"{self.base_url}/view?filename={filename}&subfolder={subfolder}"
            else:
                image_url = f"{self.base_url}/view?filename={filename}"

            # 创建输出目录
            Path(output_path).mkdir(parents=True, exist_ok=True)

            # 下载图像
            local_path = Path(output_path) / filename
            response = requests.get(image_url, stream=True, timeout=30)

            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"[OK] 图像已下载: {local_path}")
                return str(local_path)
            else:
                print(f"[ERROR] 下载失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"[ERROR] 下载图像出错: {e}")
            return None

    def get_available_checkpoints(self) -> List[str]:
        """获取可用的检查点模型列表"""
        try:
            response = requests.get(f"{self.base_url}/object_info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # CheckpointLoaderSimple节点的ckpt_name输入列表
                if "CheckpointLoaderSimple" in data:
                    ckpt_input = data["CheckpointLoaderSimple"]["input"]["required"]
                    if "ckpt_name" in ckpt_input:
                        ckpt_list = ckpt_input["ckpt_name"][0]
                        return ckpt_list
                return []
            else:
                print(f"[ERROR] 获取检查点列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"[ERROR] 获取检查点列表出错: {e}")
            return []

    def generate_athena_image(
        self, variant_name: str, prompt: str, output_dir: str = "./data/athena_comfyui"
    ) -> Optional[ComfyUIGenerationResult]:
        """
        生成Athena IP形象图像

        Args:
            variant_name: 变体名称
            prompt: 提示词
            output_dir: 输出目录

        Returns:
            生成结果
        """
        print(f"\n[ART] 生成Athena变体: {variant_name}")
        print(f"[NOTE] 提示词: {prompt[:100]}...")

        # 1. 检查服务器状态
        if not self.check_server_status():
            print("[ERROR] ComfyUI服务器未运行,请启动ComfyUI")
            return None

        # 2. 创建工作流
        negative_prompt = "低质量,模糊,变形,多余的手指,畸形,丑陋,写实照片"

        # 根据变体调整参数
        if "战斗" in variant_name:
            steps = 40
            cfg = 8.0
        elif "未来" in variant_name or "终极" in variant_name:
            steps = 50
            cfg = 9.0
        else:
            steps = 30
            cfg = 7.0

        workflow = self.create_athena_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg=cfg,
            width=1024,
            height=1024,
            seed=-1,  # 随机种子
        )

        # 3. 提交工作流
        prompt_id = self.queue_prompt(workflow)
        if not prompt_id:
            return None

        # 4. 等待完成
        if not self.wait_for_completion(prompt_id, timeout=180):
            return None

        # 5. 获取图像
        images = self.get_generated_images(prompt_id)
        if not images:
            print("[ERROR] 未找到生成的图像")
            return None

        # 6. 下载图像
        downloaded_paths = []
        for image_info in images:
            local_path = self.download_image(
                filename=image_info["filename"],
                subfolder=image_info["subfolder"],
                output_path=output_dir,
            )
            if local_path:
                downloaded_paths.append(local_path)

        if not downloaded_paths:
            return None

        # 7. 返回结果
        result = ComfyUIGenerationResult(
            image_path=downloaded_paths[0],  # 取第一张
            prompt_id=prompt_id,
            node_id=images[0]["node_id"],
            workflow=workflow,
            metadata={
                "variant_name": variant_name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "all_images": downloaded_paths,
            },
        )

        print(f"[OK] Athena图像生成成功: {result.image_path}")
        return result


def main():
    """主函数 - 测试ComfyUI集成"""
    print("🚀 Athena ComfyUI生成器测试")
    print("=" * 60)

    # 创建生成器
    generator = ComfyUIAthenaGenerator()

    # 测试服务器连接
    print("[TOOL] 检查ComfyUI服务器状态...")
    if not generator.check_server_status():
        print("""
[ERROR] ComfyUI服务器未运行!

请按以下步骤启动ComfyUI:
1. 安装ComfyUI (https://github.com/comfyanonymous/ComfyUI)
2. 启动ComfyUI服务器:
   cd /path/to/ComfyUI
   python main.py --listen
3. 确保服务器运行在 http://localhost:8188
""")
        return 1

    print("[OK] ComfyUI服务器正在运行")

    # 测试生成一个简单的Athena图像
    test_prompt = (
        "硅基共生主题的AI女神Athena,机械与生物融合的身体,"
        "发出蓝色光芒的能量核心,半透明的硅晶体皮肤,"
        "科幻漫画风格,赛博朋克,高细节"
    )

    print("\n[ART] 测试生成Athena图像...")
    result = generator.generate_athena_image(
        variant_name="测试-硅基共生", prompt=test_prompt, output_dir="./data/athena_comfyui_test"
    )

    if result:
        print(f"\n[OK] 测试成功!")
        print(f"   图像路径: {result.image_path}")
        print(f"   Prompt ID: {result.prompt_id}")
        print(f"   变体名称: {result.metadata['variant_name']}")
        return 0
    else:
        print("\n[ERROR] 测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
