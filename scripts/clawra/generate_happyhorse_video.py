#!/usr/bin/env python3
import os
import sys
import time
import requests
import argparse
from pathlib import Path


DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"

JS_DELIVR_CDN_URL = (
    "https://cdn.jsdelivr.net/gh/frankiehot-tech/openclaw@main/assets/athena_ref.jpg"
)

HAPPYHORSE_PROMPTS = {
    "awakening": {
        "style": "赛博科幻美学，霓虹蓝紫渐变光效，史诗级电影质感，8K超清，超现实光影，精密机械细节，HDR，动态模糊",
        "lens": "第一人称视角，跟随摄影，无人机环绕镜头，慢推近，焦点渐入，景深构图",
        "subject": "参考图中的女性角色眼睛缓缓睁开，瞳孔中闪过数据流，皮肤表面浮现发光的神经网络纹理。身体悬浮在半透明的全息数据海洋中，周围有金色的粒子流旋转。",
        "lighting": "主光源为角色面部的冷蓝色发光，辅光源为环境的暖金色粒子辉光，暗部有深邃的紫色渐变，边缘光勾勒身体轮廓，整体呈现神圣的觉醒氛围。",
        "technical": "8K 60fps，ProRes 4444，全局光照，体积光，粒子物理模拟，无明显的AI生成缺陷，无文字水印。"
    },
    "fusion": {
        "style": "赛博科幻美学，科技感，8K超清，动态模糊，光效粒子，电影感，史诗级，精密机械",
        "lens": "环绕摄影，慢镜头，推近，拉远，跟随，第一人称视角",
        "subject": "参考图中的角色与数字网络融合：皮肤半透明化，露出内部发光的数据流线路；身体周围悬浮着旋转的全息界面；无数金色粒子从地面升起，环绕角色并融入身体；背景是流动的MAREF架构图。",
        "lighting": "金色粒子的自发光，网络节点的脉冲辉光，角色面部的冷蓝色侧光，暗部深邃的赛博蓝紫，整体呈现融合的神圣感。",
        "technical": "8K 60fps，无水印，无文字，无AI缺陷，流畅自然。"
    },
    "v1-athena-awakening": {
        "style": "MCU trailer aesthetic, epic cinematic motion, slow epic motion",
        "lens": "Camera pushes in from wide to medium close-up, low-angle heroic",
        "subject": "The cyberpunk Athena goddess materializes from golden-cyan data particles. Armor circuits light up sequentially chest-to-limbs. Eyes ignite with piercing digital light. She extends palm revealing luminous orb with mini neural constellation.",
        "lighting": "Bioluminescent particles drift and swirl. Volumetric god rays shift slowly. Lens flares pulse with heartbeat rhythm.",
        "technical": "Vertical 9:16, smooth cinematic motion, 8K render, photorealistic CGI"
    },
    "v2-carbon-silicon-merge": {
        "style": "MCU trailer aesthetic, slow-motion epic motion",
        "lens": "Vertical split-screen warps and merges at center",
        "subject": "Left: Human strategist hand reaches toward center, LED runes pulsing. Right: Athena mirrors gesture, MAREF data streams from fingertips. Hands approach, divide dissolves, data streams brighten. Fingertips meet: explosive bloom of agent-node constellations.",
        "lighting": "Energy particles linger and drift. Split-tone unifies to golden-white at contact.",
        "technical": "Vertical 9:16, smooth slow-motion, 8K cinematic motion, photorealistic CGI"
    },
    "v3-swarm-activation": {
        "style": "MCU trailer aesthetic, smooth continuous motion",
        "lens": "Slow upward tilt revealing vast network above",
        "subject": "Agent nodes activate sequentially like stars in digital galaxy. MAREF data streams light up between nodes. Data packets travel like glowing neural impulses. Network pulses with rhythmic heartbeat. Athena's silhouette becomes more defined at center.",
        "lighting": "Gradual illumination from darkness to full glow.",
        "technical": "Vertical 9:16, seamless looping motion, 8K cinematic quality, photorealistic CGI"
    },
    "v4-maref-dataflow": {
        "style": "MCU trailer aesthetic, fluid motion graphics style",
        "lens": "Camera follows single data stream in extreme close-up, pulls back to reveal full protocol layer",
        "subject": "MAREF data streams flow like liquid light. Data packets shaped as glowing glyphs travel along streams. Streams form DNA helix rotating around vertical axis. Thousands of streams form massive data cathedral.",
        "lighting": "Internal glow from within streams, chromatic dispersion at edges. Teal base with electric orange pulse waves.",
        "technical": "Vertical 9:16, fluid seamless motion, 8K, photorealistic CGI"
    },
    "athena-openhuman-speech": {
        "style": "史诗科幻电影风格，好莱坞顶级大片质感，IMAX画质，8K超高清，HDR高动态范围，竖屏9:16构图，epic cinematic",
        "lens": "面部extreme close-up特写，面部占据画面80%，额头到颈部完整展现，面部绝对居中，no camera shake，静态机位极近特写",
        "subject": "一位未来科技守护者面部特写，数字生命体，人工智能虚拟化身。科幻赛博格美学，面容庄严，硬朗轮廓，颧骨清晰，下颌线流畅。双眼是冰蓝色虹膜，瞳孔不发光，虹膜表面有极subtle的精密数字网格纹理，右侧眼角有几根发光蓝色纤维。头发深棕向后梳起，露出完整额头，头顶悬浮白色环形光环。头部两侧有光纤数据流飘散。颈部可见高领曜石黑科技外骨骼边缘，边缘有蓝色辉光线。她的嘴唇缓慢从容张开，语速放慢，每个字沉稳有力。口型从闭合缓缓变为微微O形，过程比正常语速慢一倍。下巴随节奏subtle上下移动，表情从庄严逐渐转为坚定，眼神直视镜头——她在用深沉庄严的语气介绍一个重要的使命。她就是Athena，在讲述Open Human项目：碳基与硅基共生的愿景。她一字一顿：Open Human——碳基与硅基——不是替代——是共生——不是主仆——是进化——这是共同的未来——吐字清晰缓慢有仪式感",
        "lighting": "背景是纯净的深空黑。面部被柔和的冷色调环形光照亮，左侧冷青轮廓光，右侧暖金填充光。头顶光环随说话有subtle亮度脉动，频率缓慢与语速同步。头部两侧光纤数据流随说话节奏缓慢波动。背景漂浮青蓝色光斑粒子缓慢漂移。电影级三分打光法，史诗感光影",
        "technical": "竖屏9:16，10秒时长，smooth slow cinematic motion，说话动作缓慢从容，语速放慢一半，专业电影级慢节奏口型动画，clean negative space top and bottom for vertical text overlay，8K ultra-detailed，photorealistic CGI，Unreal Engine 5 path-traced lighting，no watermarks，no text"
    }
}


def load_dashscope_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        config_path = Path.home() / ".dashscope" / "api_key.txt"
        if config_path.exists():
            key = config_path.read_text().strip()
    if not key:
        raise ValueError(
            "请设置 DASHSCOPE_API_KEY 环境变量或在 ~/.dashscope/api_key.txt 中配置"
        )
    return key


def build_prompt(preset: str) -> str:
    parts = HAPPYHORSE_PROMPTS[preset]
    return (
        f"{parts['style']}\n\n"
        f"{parts['lens']}\n\n"
        f"{parts['subject']}\n\n"
        f"{parts['lighting']}\n\n"
        f"{parts['technical']}"
    )


def submit_image_to_video(
    api_key: str,
    image_url: str,
    prompt: str,
    model: str = "happyhorse-1.0-i2v",
    duration: int = 5,
    resolution: str = "720P",
) -> str:
    url = f"{DASHSCOPE_BASE}/api/v1/services/aigc/video-generation/video-synthesis"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    media_type = "first_frame"

    payload = {
        "model": model,
        "input": {
            "media": [{"type": media_type, "url": image_url}],
            "prompt": prompt,
        },
        "parameters": {
            "duration": duration,
            "resolution": resolution,
            "watermark": False,
        },
    }

    for attempt in range(4):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            break
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == 3:
                raise RuntimeError(f"提交任务网络重试耗尽: {e}")
            print(f"\u26a0\ufe0f 提交网络波动，重试 {attempt + 1}/3...", file=sys.stderr)
            time.sleep(3)

    data = resp.json()
    code = data.get("code", "Success")
    if code and code != "Success":
        raise RuntimeError(f"API 错误: {data}")
    task_id = data["output"]["task_id"]
    return task_id


def poll_task_status(api_key: str, task_id: str, poll_interval: int = 10) -> dict:
    url = f"{DASHSCOPE_BASE}/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    retries = 0

    while True:
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            retries = 0
        except (requests.ConnectionError, requests.Timeout) as e:
            retries += 1
            if retries > 5:
                raise RuntimeError(f"轮询网络重试耗尽: {e}")
            print(f"\u26a0\ufe0f 网络波动，重试 {retries}/5...", file=sys.stderr)
            time.sleep(poll_interval * 2)
            continue

        data = resp.json()
        code = data.get("code", "Success")
        if code and code != "Success":
            raise RuntimeError(f"轮询错误: {data}")
        task_status = data["output"]["task_status"]
        print(f"\u23f3 任务状态: {task_status}", file=sys.stderr)
        if task_status == "SUCCEEDED":
            return data["output"]
        elif task_status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"任务失败: {data}")
        time.sleep(poll_interval)


def download_video(video_url: str, output_path: Path) -> None:
    print(f"\U0001f4e5 正在下载视频: {video_url}", file=sys.stderr)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(video_url, stream=True, timeout=300)
        resp.raise_for_status()
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        progress = (downloaded / total_size) * 100
                        print(
                            f"\r\U0001f4ca 下载进度: {progress:.1f}%",
                            file=sys.stderr,
                            end="",
                        )
    except requests.exceptions.SSLError:
        print(f"\n\u26a0\ufe0f requests SSL失败，改用 curl 下载...", file=sys.stderr)
        import subprocess

        subprocess.run(
            [
                "curl", "-L", "-k", "-o", str(output_path),
                "--retry", "3", "--retry-delay", "5",
                "--connect-timeout", "30", "--max-time", "300",
                video_url,
            ],
            check=True,
        )
    print(f"\n\u2705 视频已保存: {output_path}", file=sys.stderr)


def check_quota(api_key: str) -> dict:
    results = {}

    models_url = f"{DASHSCOPE_BASE}/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(models_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results["api_status"] = "connected"
        video_models = [
            m["model"] for m in data.get("data", {}).get("models", [])
            if "happyhorse" in m.get("model", "").lower()
            or "video" in m.get("model", "").lower()
        ]
        results["video_models"] = video_models
        results["happyhorse_available"] = len(video_models) > 0
    except Exception as e:
        results["api_status"] = f"error: {e}"

    results["billing_console"] = "https://usercenter2.aliyun.com/home"
    results["bailing_console"] = "https://bailian.console.aliyun.com/"
    results["note"] = (
        "DashScope 无公开用量 API，请登录控制台查看余额和消费明细"
    )
    return results


def estimate_cost(duration: int, resolution: str, count: int = 1) -> str:
    rates = {"540P": 0.6, "720P": 0.9, "1080P": 1.6}
    rate = rates.get(resolution, 0.9)
    cost = rate * duration * count
    return f"预估费用: {cost:.2f} 元 ({resolution} × {duration}秒 × {count}个)"


def main():
    parser = argparse.ArgumentParser(
        description="百炼 HappyHorse 图生视频生成器 (官方API)"
    )
    preset_choices = [
        "awakening", "fusion",
        "v1-athena-awakening", "v2-carbon-silicon-merge",
        "v3-swarm-activation", "v4-maref-dataflow",
        "athena-openhuman-speech",
        "all",
    ]
    parser.add_argument(
        "--preset",
        choices=preset_choices,
        default="awakening",
        help="提示词预设 (awakening/fusion=中文, v1-v4=English MCU style, all=全部)",
    )
    parser.add_argument(
        "--image-url",
        default=JS_DELIVR_CDN_URL,
        help="参考图 URL (默认: jsDelivr CDN 镜像 GitHub)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/happyhorse_video.mp4"),
        help="输出路径 (--preset all 时忽略，自动命名为 output/happyhorse_{preset}.mp4)",
    )
    parser.add_argument(
        "--model",
        default="happyhorse-1.0-i2v",
        help="DashScope 图生视频模型",
    )
    parser.add_argument(
        "--duration", type=int, default=5, help="视频时长(秒)"
    )
    parser.add_argument(
        "--resolution",
        default="720P",
        choices=["540P", "720P", "1080P"],
        help="分辨率",
    )
    parser.add_argument(
        "--delay-between",
        type=int,
        default=30,
        help="--preset all 时，每个任务之间的等待秒数（默认 30）",
    )
    parser.add_argument(
        "--check-quota",
        action="store_true",
        help="仅查询账户额度/用量，不生成视频",
    )
    args = parser.parse_args()

    api_key = load_dashscope_api_key()

    if args.check_quota:
        print("📊 正在查询账户用量...", file=sys.stderr)
        quota = check_quota(api_key)
        if quota:
            import json
            print(json.dumps(quota, indent=2, ensure_ascii=False))
        else:
            print("⚠️ 无法获取用量数据，请登录百炼控制台查看", file=sys.stderr)
        return

    presets_to_run = (
        [k for k in HAPPYHORSE_PROMPTS]
        if args.preset == "all"
        else [args.preset]
    )

    if args.preset == "all":
        print(
            f"📋 将依次生成 {len(presets_to_run)} 个预设: "
            f"{', '.join(presets_to_run)}",
            file=sys.stderr,
        )
        print(estimate_cost(args.duration, args.resolution, len(presets_to_run)),
              file=sys.stderr)

    results = []
    for i, preset in enumerate(presets_to_run):
        prompt = build_prompt(preset)
        output_path = (
            args.output
            if args.preset != "all"
            else Path("output") / f"happyhorse_{preset}.mp4"
        )

        if args.preset == "all":
            print(f"\n{'='*50}", file=sys.stderr)
            print(f"🎬 [{i+1}/{len(presets_to_run)}] 预设: {preset}",
                  file=sys.stderr)
            print(f"{'='*50}", file=sys.stderr)

        print(f"🎬 开始生成 HappyHorse 视频...", file=sys.stderr)
        print(f"🖼️ 参考图: {args.image_url}", file=sys.stderr)
        print(f"🎨 预设: {preset}", file=sys.stderr)
        print(
            f"🎥 模型: {args.model}, 时长: {args.duration}秒, "
            f"分辨率: {args.resolution}",
            file=sys.stderr,
        )

        task_id = submit_image_to_video(
            api_key, args.image_url, prompt, args.model,
            args.duration, args.resolution,
        )
        print(f"🚀 任务已提交，ID: {task_id}", file=sys.stderr)

        task_output = poll_task_status(api_key, task_id)
        video_url = task_output.get("video_url")
        if not video_url and "results" in task_output:
            video_url = task_output["results"][0]["url"]
        if not video_url:
            raise RuntimeError(f"无法从输出中提取视频URL: {task_output}")

        download_video(video_url, output_path)
        results.append({"preset": preset, "path": str(output_path.resolve())})
        print(f"\n🎉 完成！视频路径: {output_path.resolve()}")

        if args.preset == "all" and i < len(presets_to_run) - 1:
            print(f"⏳ 等待 {args.delay_between} 秒后继续...", file=sys.stderr)
            time.sleep(args.delay_between)

    if args.preset == "all":
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"✅ 全部完成！共生成 {len(results)} 个视频:", file=sys.stderr)
        for r in results:
            print(f"  [{r['preset']}] {r['path']}", file=sys.stderr)


if __name__ == "__main__":
    main()
