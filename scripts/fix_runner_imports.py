#!/usr/bin/env python3
"""Add missing stdlib imports to all runner module files."""
from pathlib import Path

RUNNER_DIR = Path(__file__).resolve().parent / "runner"

STDLIB_IMPORTS = [
    "import json",
    "import re",
    "import shutil",
    "import signal",
    "import subprocess",
    "import time",
]

for f in sorted(RUNNER_DIR.glob("*.py")):
    if f.name == "__init__.py":
        continue

    content = f.read_text()
    lines = content.split("\n")

    # Find which stdlib imports are missing
    missing = []
    for imp in STDLIB_IMPORTS:
        mod = imp.split()[1]
        if f"import {mod}" not in content and f"from {mod}" not in content:
            missing.append(imp)

    if not missing:
        print(f"  OK: {f.name}")
        continue

    # Find insert position: after the last existing import
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from __future__"):
            insert_idx = i + 1

    for imp in sorted(missing):
        lines.insert(insert_idx, imp)
        insert_idx += 1

    f.write_text("\n".join(lines))
    print(f"  FIXED: {f.name} (+{', '.join(missing)})")
