"""PreToolUse hook: 提交前运行 ruff + mypy 快速检查"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
os.chdir(project_root)

venv_bin = project_root / ".venv" / "bin"

def find_tool(name: str) -> str:
    venv_path = venv_bin / name
    if venv_path.exists():
        return str(venv_path)
    return shutil.which(name) or name

errors = []

r = subprocess.run(
    [find_tool("ruff"), "check", "scripts/", "athena/", "execution/", "ops/", "--output-format=concise"],
    capture_output=True, text=True
)
if r.returncode != 0:
    errors.append(f"ruff check failed:\n{r.stdout}\n{r.stderr}")

r = subprocess.run(
    [find_tool("mypy"), "scripts/", "athena/", "execution/", "ops/",
     "--ignore-missing-imports", "--show-error-codes", "--no-error-summary"],
    capture_output=True, text=True
)
if r.returncode != 0:
    errors.append(f"mypy failed:\n{r.stdout[:2000]}\n{r.stderr[:500]}")

if errors:
    print("\n" + "=" * 60, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Pre-commit checks failed. Fix issues or use --no-verify to bypass.", file=sys.stderr)
    sys.exit(2)

print("pre_commit: ruff + mypy OK")
sys.exit(0)
