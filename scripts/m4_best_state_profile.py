#!/usr/bin/env python3
"""M4 Best State Profile - Output structured snapshot of current system state.

Generates a human-readable summary and JSON snapshot of CPU, memory, load,
Ollama activity, and build worker budget recommendations.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    import system_resource_facts
except ImportError as e:
    print(f"Error: Failed to import system_resource_facts: {e}")
    sys.exit(1)


def main() -> int:
    """Collect and display best state profile."""
    print("Collecting M4 best state profile...")

    # Collect resource facts
    facts = system_resource_facts.collect_resource_facts()

    # Extract key metrics
    cpu = facts.get("cpu", {})
    memory = facts.get("memory", {})
    runner = facts.get("runner", {})

    # Determine single/dual build worker recommendation
    budget = runner.get("budget", 1)
    recommendation = "single build worker" if budget == 1 else "dual build workers"
    reason = runner.get("reason", "")

    # Create structured snapshot
    snapshot = {
        "sampled_at": facts.get("sampled_at"),
        "machine_profile": "local_m4_safe_mode",
        "cpu": {
            "usage_percent": cpu.get("usage_percent"),
            "user_percent": cpu.get("user_percent"),
            "system_percent": cpu.get("system_percent"),
            "load_average": cpu.get("load_average"),
            "core_count": cpu.get("core_count"),
        },
        "memory": {
            "total_gb": memory.get("total_gb"),
            "pressure_free_percent": memory.get("pressure_free_percent"),
            "pressure_used_percent": memory.get("pressure_used_percent"),
            "available_gb": memory.get("available_gb"),
            "app_gb": memory.get("app_gb"),
            "compressed_gb": memory.get("compressed_gb"),
        },
        "ollama": {
            "cpu_percent": runner.get("ollama_cpu_percent"),
        },
        "build_worker_budget": {
            "recommended": budget,
            "recommendation": recommendation,
            "reason": reason,
            "max_build_workers": runner.get("max_build_workers"),
            "second_build_min_free_memory_percent": runner.get(
                "second_build_min_free_memory_percent"
            ),
            "max_build_load_per_core": runner.get("max_build_load_per_core"),
            "max_build_load_absolute": runner.get("max_build_load_absolute"),
            "ollama_busy_cpu_percent": runner.get("ollama_busy_cpu_percent"),
        },
        "full_facts": facts,
    }

    # Output JSON
    json_output = json.dumps(snapshot, ensure_ascii=False, indent=2)

    # Output human-readable summary
    print("\n" + "=" * 60)
    print("M4 BEST STATE PROFILE")
    print("=" * 60)
    print(f"Sampled at: {snapshot['sampled_at']}")
    print(f"Machine profile: {snapshot['machine_profile']}")
    print()
    print("CPU:")
    print(
        f"  Usage: {snapshot['cpu']['usage_percent']}% (user {snapshot['cpu']['user_percent']}%, system {snapshot['cpu']['system_percent']}%)"
    )
    print(
        f"  Load average: {snapshot['cpu']['load_average'][0]:.2f}, {snapshot['cpu']['load_average'][1]:.2f}, {snapshot['cpu']['load_average'][2]:.2f}"
    )
    print(f"  Cores: {snapshot['cpu']['core_count']}")
    print()
    print("Memory:")
    print(f"  Total: {snapshot['memory']['total_gb']} GB")
    print(f"  Free pressure: {snapshot['memory']['pressure_free_percent']}%")
    print(f"  Available: {snapshot['memory']['available_gb']} GB")
    print(f"  App memory: {snapshot['memory']['app_gb']} GB")
    print(f"  Compressed: {snapshot['memory']['compressed_gb']} GB")
    print()
    print("Ollama:")
    print(f"  CPU activity: {snapshot['ollama']['cpu_percent']}%")
    print()
    print("Build Worker Budget:")
    print(
        f"  Recommended: {snapshot['build_worker_budget']['recommended']} ({snapshot['build_worker_budget']['recommendation']})"
    )
    print(f"  Reason: {snapshot['build_worker_budget']['reason']}")
    print(f"  Max workers: {snapshot['build_worker_budget']['max_build_workers']}")
    print(
        f"  Min free memory for second worker: {snapshot['build_worker_budget']['second_build_min_free_memory_percent']}%"
    )
    print(f"  Max load per core: {snapshot['build_worker_budget']['max_build_load_per_core']}")
    print(f"  Max absolute load: {snapshot['build_worker_budget']['max_build_load_absolute']}")
    print(f"  Ollama busy threshold: {snapshot['build_worker_budget']['ollama_busy_cpu_percent']}%")
    print()
    print("=" * 60)
    print("Full JSON snapshot available below.")
    print("=" * 60)
    print(json_output)

    # Write snapshot to workspace
    workspace_dir = Path("/Volumes/1TB-M2/openclaw/workspace/m4_best_state")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = workspace_dir / f"m4_best_state_profile_{timestamp}.json"
    json_path.write_text(json_output, encoding="utf-8")

    print(f"\nSnapshot saved to: {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
