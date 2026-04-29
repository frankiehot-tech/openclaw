"""PreToolUse hook: 推送前运行安全扫描"""
import subprocess
import sys
import shutil
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

venv_bin = project_root / ".venv" / "bin"

def find_tool(name: str) -> str:
    venv_path = venv_bin / name
    if venv_path.exists():
        return str(venv_path)
    return shutil.which(name) or name

errors = []

r = subprocess.run(
    [find_tool("bandit"), "-r", "scripts/", "execution/", "ops/", "-f", "json", "-q"],
    capture_output=True, text=True, cwd=str(project_root)
)
if r.returncode != 0:
    errors.append(f"bandit scan failed:\n{r.stdout[:2000]}")

r = subprocess.run(
    [find_tool("pip-audit"), "--desc"],
    capture_output=True, text=True, cwd=str(project_root)
)
if r.returncode != 0:
    errors.append(f"pip-audit found vulnerabilities:\n{r.stdout[:2000]}")

if errors:
    print("\n" + "=" * 60, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Pre-push security checks failed. Fix issues before pushing.", file=sys.stderr)
    sys.exit(2)

print("pre_push: bandit + pip-audit OK")
sys.exit(0)
