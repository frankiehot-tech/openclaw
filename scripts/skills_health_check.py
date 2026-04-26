#!/usr/bin/env python3
"""Skills health check: 验证 ~/.claude/skills/ 中所有 symlink 和文件的有效性"""

import os
import sys
from pathlib import Path

SKILLS_DIR = os.path.expanduser("~/.claude/skills")
BUN_CACHE_PREFIX = os.path.expanduser("~/.bun/install/cache/")

def check_skills():
    if not os.path.exists(SKILLS_DIR):
        print(f"ERROR: Skills directory not found: {SKILLS_DIR}")
        return 1

    errors = []
    warnings = []
    ok = 0

    for entry in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, entry)

        if os.path.islink(path):
            target = os.readlink(path)
            if os.path.exists(path):
                ok += 1
            else:
                errors.append(f"BROKEN SYMLINK: {entry} → {target}")
        elif entry.endswith(".md") or entry.endswith(".json"):
            if os.path.getsize(path) == 0:
                warnings.append(f"EMPTY FILE: {entry}")
            else:
                ok += 1
        elif os.path.isdir(path):
            ok += 1  # directory skills ok
        elif entry.endswith(".backup"):
            continue  # skip backups
        else:
            warnings.append(f"UNKNOWN TYPE: {entry}")

    print(f"Skills health: {ok} OK, {len(warnings)} warnings, {len(errors)} errors")

    for w in warnings:
        print(f"  WARN: {w}")
    for e in errors:
        print(f"  ERROR: {e}")

    # Check bun cache drift
    bun_links = []
    for entry in os.listdir(SKILLS_DIR):
        path = os.path.join(SKILLS_DIR, entry)
        if os.path.islink(path):
            target = os.readlink(path)
            if target.startswith(BUN_CACHE_PREFIX):
                bun_links.append((entry, target))

    if bun_links:
        # All bun links should have the same cache prefix
        prefixes = set()
        for name, target in bun_links:
            parts = target.replace(BUN_CACHE_PREFIX, "").split("/")
            if parts:
                prefixes.add(parts[0])
        if len(prefixes) > 1:
            warnings.append(f"BUN CACHE DRIFT: {len(prefixes)} different cache prefixes detected")
            for name, target in bun_links:
                warnings.append(f"  {name} → {target}")
        else:
            print(f"Bun cache: {len(bun_links)} symlinks, prefix consistent")

    return len(errors)


if __name__ == "__main__":
    sys.exit(check_skills())
