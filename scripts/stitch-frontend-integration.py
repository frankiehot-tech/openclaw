#!/usr/bin/env python3
"""
Integration script for Stitch frontend with Athena control plane.
This script helps connect the frontend workspace with the wider OpenClaw ecosystem.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "workspace" / "stitch-frontend"
MINI_AGENT_DIR = WORKSPACE_ROOT / "mini-agent"
CONFIG_FILE = MINI_AGENT_DIR / "config" / "stitch-frontend.json"


def check_frontend():
    """Verify frontend workspace structure"""
    print("🔍 Checking Stitch frontend workspace...")

    if not FRONTEND_DIR.exists():
        print(f"❌ Frontend directory not found: {FRONTEND_DIR}")
        return False

    required_files = [
        "package.json",
        "next.config.mjs",
        "src/app/layout.tsx",
        "src/app/page.tsx",
    ]

    all_ok = True
    for file in required_files:
        path = FRONTEND_DIR / file
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_ok = False

    return all_ok


def check_config():
    """Verify integration configuration"""
    print("\n🔧 Checking integration configuration...")

    if not CONFIG_FILE.exists():
        print(f"❌ Config file not found: {CONFIG_FILE}")
        return False

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)

        print(f"  ✅ Config file loaded")
        print(f"  📋 Frontend: {config.get('frontend', {}).get('name', 'unknown')}")
        print(
            f"  🚀 Features: {', '.join([k for k, v in config.get('frontend', {}).get('features', {}).items() if v])}"
        )
        return True
    except Exception as e:
        print(f"  ❌ Error loading config: {e}")
        return False


def check_dependencies():
    """Check if frontend dependencies are installed"""
    print("\n📦 Checking dependencies...")

    node_modules = FRONTEND_DIR / "node_modules"
    package_json = FRONTEND_DIR / "package.json"

    if not node_modules.exists():
        print("  ⚠️  node_modules not found - run 'npm install' in frontend directory")
        return False
    else:
        print("  ✅ Dependencies installed")
        return True


def start_frontend_dev():
    """Start the frontend development server"""
    print("\n🚀 Starting frontend development server...")

    if not check_frontend():
        print("Cannot start server due to missing files.")
        return False

    try:
        # This would actually start the server; for now just show command
        print("  Run manually:")
        print(f"    cd {FRONTEND_DIR}")
        print("    npm run dev")
        print("\n  Or use the provided script:")
        print(f"    {FRONTEND_DIR}/scripts/start-dev.sh")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("🔄 Stitch Frontend Integration Check")
    print("=" * 40)

    frontend_ok = check_frontend()
    config_ok = check_config()
    deps_ok = check_dependencies()

    print("\n📊 Summary:")
    print(f"  Frontend workspace: {'✅' if frontend_ok else '❌'}")
    print(f"  Integration config: {'✅' if config_ok else '❌'}")
    print(f"  Dependencies: {'✅' if deps_ok else '⚠️ '}")

    if frontend_ok and config_ok:
        print("\n🎉 Integration ready!")
        print("\nNext steps:")
        print("  1. Install dependencies: cd workspace/stitch-frontend && npm install")
        print("  2. Start dev server: cd workspace/stitch-frontend && npm run dev")
        print("  3. Access at http://localhost:3000")
    else:
        print("\n⚠️  Some issues found. Please fix before proceeding.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
