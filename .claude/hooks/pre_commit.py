"""PreToolUse hook: 提交前运行 ruff + mypy 快速检查"""
import subprocess
import sys
import os

os.chdir("/Volumes/1TB-M2/openclaw")

errors = []

# ruff check
r = subprocess.run(
    ["ruff", "check", "scripts/", "athena/", "execution/", "ops/", "--output-format=concise"],
    capture_output=True, text=True
)
if r.returncode != 0:
    errors.append(f"ruff check failed:\n{r.stdout}\n{r.stderr}")

# mypy quick
r = subprocess.run(
    ["mypy", "scripts/", "athena/", "execution/", "ops/",
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
    sys.exit(1)

print("pre_commit: ruff + mypy OK")
sys.exit(0)
