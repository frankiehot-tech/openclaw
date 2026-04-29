"""PostToolUse hook: 文件写入后自动格式化 Python 文件"""
import subprocess
import sys
import json
from pathlib import Path

try:
    hook_input = json.load(sys.stdin)
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
except (json.JSONDecodeError, EOFError):
    file_path = ""

if not file_path.endswith(".py"):
    sys.exit(0)

project_root = Path(__file__).resolve().parent.parent.parent
venv_ruff = project_root / ".venv" / "bin" / "ruff"
ruff_cmd = str(venv_ruff) if venv_ruff.exists() else "ruff"

r = subprocess.run(
    [ruff_cmd, "format", file_path],
    capture_output=True, text=True, cwd=str(project_root)
)
if r.returncode != 0:
    print(f"ruff format failed for {file_path}: {r.stderr}", file=sys.stderr)

sys.exit(0)
