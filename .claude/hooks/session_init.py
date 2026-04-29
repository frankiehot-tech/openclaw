"""SessionStart hook: 会话启动时输出项目状态摘要"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
os.chdir(project_root)

print("\n" + "=" * 60)
print("OpenClaw 项目状态摘要")
print("=" * 60)

memory_path = project_root / "MEMORY.md"
if memory_path.exists():
    with open(memory_path, "r") as f:
        lines = f.readlines()
    print("\n[MEMORY.md 关键决策]")
    for line in lines[:20]:
        if line.strip() and not line.startswith("#"):
            print(f"  {line.rstrip()}")

state_path = project_root / "STATE.yaml"
if state_path.exists():
    with open(state_path, "r") as f:
        content = f.read()
    print("\n[STATE.yaml 当前状态]")
    for line in content.split("\n")[:15]:
        if line.strip():
            print(f"  {line}")

venv_path = project_root / ".venv" / "bin"
if venv_path.exists():
    print(f"\n[虚拟环境] {venv_path}")
    tools = ["ruff", "mypy", "bandit", "pip-audit", "pytest"]
    for t in tools:
        if (venv_path / t).exists():
            print(f"  ✅ {t}")
        else:
            print(f"  ❌ {t} (未安装)")

print("\n" + "=" * 60)
sys.exit(0)
