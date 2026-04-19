#!/usr/bin/env python3
"""
Kdenlive集成模块 - 将Kdenlive CLI广告级视频工作流集成到Clawra
基于ROMA/external/kdenlive_workflow_repl.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_kdenlive_repl(commands, project_file=None):
    """通过管道运行Kdenlive REPL命令"""
    # 创建临时文件包含命令
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for cmd in commands:
            f.write(cmd + "\n")
        f.write("quit\n")
        script_file = f.name

    try:
        cmd = ["python3", "-m", "cli_anything.kdenlive.kdenlive_cli"]
        if project_file:
            cmd.extend(["--project", project_file])

        print(f"运行REPL命令:")
        for c in commands:
            print(f"  {c}")

        with open(script_file, "r") as infile:
            result = subprocess.run(cmd, stdin=infile, capture_output=True, text=True, timeout=60)

        os.unlink(script_file)

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            return False, f"REPL失败: {error}"

        # 尝试从输出解析JSON
        lines = output.split("\n")
        json_lines = [l for l in lines if l.strip().startswith("{") and l.strip().endswith("}")]

        if json_lines:
            try:
                last_json = json.loads(json_lines[-1])
                return True, last_json
            except:
                pass

        return True, output

    except Exception as e:
        return False, str(e)


def create_ad_level_video_project(
    output_dir=None,
    project_name="广告级视频演示",
    width=1920,
    height=1080,
    fps_num=30,
    fps_den=1,
    duration=15,
):
    """
    创建广告级视频项目

    Args:
        output_dir: 输出目录（如果为None则创建临时目录）
        project_name: 项目名称
        width: 视频宽度
        height: 视频高度
        fps_num: 帧率分子
        fps_den: 帧率分母
        duration: 视频时长（秒）

    Returns:
        (success, project_file, xml_file) 元组
    """
    print("=== 创建广告级视频项目 ===")

    # 创建输出目录
    if output_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="ad_video_")
        output_dir = temp_dir
    else:
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = output_dir

    project_file = os.path.join(output_dir, f"{project_name}.kdenlive-cli.json")
    output_xml = os.path.join(output_dir, f"{project_name}.xml")

    print(f"工作目录: {output_dir}")
    print(f"项目文件: {project_file}")
    print(f"输出XML: {output_xml}")

    # 广告级视频标准参数
    project_name = project_name.replace("'", "''")  # 转义单引号

    # 工作流命令序列
    commands = [
        # 1. 创建项目
        f"project new --name '{project_name}' --width {width} --height {height} --fps-num {fps_num} --fps-den {fps_den}",
        f"project save {project_file}",
        # 2. 添加视频轨道
        "timeline add-track --type video --name V1",
        "timeline add-track --type video --name V2",
        # 3. 添加音频轨道
        "timeline add-track --type audio --name A1",
        "timeline add-track --type audio --name A2",
        # 4. 导入素材
        # 4.1 背景颜色剪辑
        f"bin import color --type color --name bg_gradient --duration {duration}",
        # 4.2 标题文字剪辑
        f"bin import color --type title --name title_intro --duration 3",
        # 4.3 产品展示剪辑
        f"bin import color --type color --name product_shot --duration 5",
        # 4.4 号召性用语剪辑
        f"bin import color --type title --name call_to_action --duration 4",
        # 5. 将剪辑添加到时间线
        # 5.1 背景渐变（轨道V1，位置0）
        "timeline add-clip 0 clip0 --position 0.0",
        # 5.2 标题介绍（轨道V2，位置0，叠加在背景上）
        "timeline add-clip 1 clip1 --position 0.0",
        # 5.3 产品展示（轨道V2，位置3，淡入标题）
        "timeline add-clip 1 clip2 --position 3.0",
        # 5.4 号召性用语（轨道V2，位置8）
        "timeline add-clip 1 clip3 --position 8.0",
        # 6. 添加转场效果（暂时注释，需要修复语法）
        # "transition add --type fade --position 3.0 --duration 1.0 --track 1",
        # "transition add --type fade --position 8.0 --duration 1.0 --track 1",
        # 7. 添加滤镜效果
        "filter add --type brightness --track 0 --clip clip0 --params brightness=0.1",
        "filter add --type saturation --track 1 --clip clip1 --params saturation=1.2",
        # 8. 添加时间线标记（暂时注释，需要修复语法）
        # "guide add --position 0.0 --name '开始'",
        # "guide add --position 3.0 --name '标题淡出'",
        # "guide add --position 8.0 --name '产品展示'",
        # "guide add --position 12.0 --name '号召性用语'",
        # "guide add --position 15.0 --name '结束'",
        # 9. 检查项目状态
        "project info",
        # 10. 导出MLT XML（供Kdenlive/melt使用）
        f"export xml --output {output_xml}",
        # 11. 保存项目
        "project save",
    ]

    # 执行工作流
    print("\n执行视频工作流...")
    success, result = run_kdenlive_repl(commands, project_file=None)

    if success:
        print(f"\n✅ 广告级视频项目创建成功")
        print(f"项目文件: {project_file}")
        print(f"XML输出: {output_xml}")

        # 显示项目摘要
        if os.path.exists(project_file):
            with open(project_file, "r") as f:
                project_data = json.load(f)

            tracks = project_data.get("tracks", [])
            bin_clips = project_data.get("bin", [])
            guides = project_data.get("guides", [])

            print(f"\n项目摘要:")
            print(f"  名称: {project_data.get('name', 'N/A')}")
            print(
                f"  分辨率: {project_data.get('profile', {}).get('width', 'N/A')}x{project_data.get('profile', {}).get('height', 'N/A')}"
            )
            print(
                f"  帧率: {project_data.get('profile', {}).get('fps_num', 'N/A')}/{project_data.get('profile', {}).get('fps_den', 'N/A')}"
            )
            print(f"  轨道数: {len(tracks)}")
            print(f"  素材库剪辑数: {len(bin_clips)}")
            print(f"  时间线标记数: {len(guides)}")

            # 显示轨道详情
            print(f"\n轨道详情:")
            for i, track in enumerate(tracks):
                print(
                    f"  [{i}] {track['name']} ({track['type']}): {len(track.get('clips', []))} 个剪辑"
                )

        # 检查XML输出
        if os.path.exists(output_xml):
            file_size = os.path.getsize(output_xml)
            print(f"\nMLT XML文件生成成功:")
            print(f"  大小: {file_size} 字节")
            print(f"  路径: {output_xml}")

            # 显示XML前几行
            with open(output_xml, "r") as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            print(f"  XML预览:")
            for line in first_lines:
                if line:
                    print(f"    {line}")

        return True, project_file, output_xml

    else:
        print(f"\n❌ 工作流执行失败: {result}")
        return False, None, None


def test_integration():
    """测试集成功能"""
    print("=== 测试Kdenlive集成模块 ===")

    # 创建测试目录
    test_dir = "/tmp/clawra_kdenlive_test"
    os.makedirs(test_dir, exist_ok=True)

    print(f"测试目录: {test_dir}")

    # 创建广告级视频项目
    success, project_file, xml_file = create_ad_level_video_project(
        output_dir=test_dir,
        project_name="集成测试视频",
        width=1280,
        height=720,
        fps_num=30,
        fps_den=1,
        duration=10,
    )

    if success:
        print(f"\n✅ 集成测试成功")
        print(f"项目文件: {project_file}")
        print(f"XML文件: {xml_file}")
        return True
    else:
        print(f"\n❌ 集成测试失败")
        return False


if __name__ == "__main__":
    # 运行测试
    if test_integration():
        print("\n✅ Kdenlive集成模块测试通过")
        sys.exit(0)
    else:
        print("\n❌ Kdenlive集成模块测试失败")
        sys.exit(1)
