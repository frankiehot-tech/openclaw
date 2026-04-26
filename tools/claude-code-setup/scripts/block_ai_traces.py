#!/usr/bin/env python3
"""Pre-commit hook script to block AI工具 traces from being committed."""
import sys
import re

BLOCK_PATTERNS = [
    re.compile(r'ai\s*code', re.IGNORECASE),
    re.compile(r'llm', re.IGNORECASE),
    re.compile(r'generated\s*by\s*ai', re.IGNORECASE),
    re.compile(r'LLM_API_KEY'),
    re.compile(r'AI_MODEL'),
    re.compile(r'AI_'),
    re.compile(r'LLM_'),
]

# Directories to skip
SKIP_DIRS = ('node_modules/', '.git/', 'venv/', '__pycache__/', 'reference/')

def check_file(filepath):
    """Check a single file for blocked patterns."""
    # Skip certain directories
    if any(filepath.startswith(d) for d in SKIP_DIRS):
        return True

    # Skip binary files
    if filepath.endswith(('.pyc', '.png', '.jpg', '.gif', '.ico', '.woff', '.eot', '.woff2')):
        return True

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for i, line in enumerate(content.split('\n'), 1):
                for pattern in BLOCK_PATTERNS:
                    if pattern.search(line):
                        print(f"  {filepath}:{i}: {line.strip()[:80]}")
                        return False
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return True
    return True


def check_filename(filepath):
    """Check if filename contains blocked patterns."""
    basename = filepath.split('/')[-1].lower()
    if 'ai' in basename or 'llm' in basename:
        print(f"  Filename: {filepath}")
        return False
    return True


if __name__ == "__main__":
    files = sys.argv[1:]
    violations = []

    for f in files:
        if not check_filename(f):
            violations.append(f)
        elif not check_file(f):
            violations.append(f)

    if violations:
        print(f"\nPre-commit check FAILED: {len(violations)} file(s) contain AI工具 traces")
        print("Please clean these files before committing.")
        sys.exit(1)

    print("Pre-commit check passed: No AI tool traces detected.")
    sys.exit(0)