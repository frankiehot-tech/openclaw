#!/usr/bin/env python3
"""Athena AutoResearch runner.

Integrates the AutoResearch engine into the Athena workflow system.
Can run as a standalone daemon, triggered by events, or manually.

Safety constraints:
- Only runs when explicitly enabled (ATHENA_AUTORESEARCH_ENABLED=1)
- Dry-run by default, requires explicit flag to apply changes
- All recommendations go through constraint gates
- Failures are isolated and logged, never crash main runners
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Import shared root paths
try:
    from .openclaw_roots import RUNTIME_ROOT, pid_file
except ImportError:
    # fallback for direct script execution
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import RUNTIME_ROOT, pid_file

# Import AutoResearch engine
try:
    from .athena_autoresearch_engine import AutoResearchEngine, ResearchResult
except ImportError:
    # fallback
    sys.path.insert(0, str(scripts_dir))
    from athena_autoresearch_engine import AutoResearchEngine, ResearchResult

# Try to import event bus for integration
try:
    # Add mini-agent path for event bus import
    mini_agent_path = RUNTIME_ROOT / "mini-agent"
    if str(mini_agent_path) not in sys.path:
        sys.path.insert(0, str(mini_agent_path))
    from agent.core.event_bus import EventType, get_bus

    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
PID_FILE = pid_file("athena_autoresearch_runner")
POLL_SECONDS = int(os.getenv("ATHENA_AUTORESEARCH_POLL_SECONDS", "3600"))  # 1 hour default
ENABLED = os.getenv("ATHENA_AUTORESEARCH_ENABLED", "0") == "1"
DRY_RUN_DEFAULT = os.getenv("ATHENA_AUTORESEARCH_DRY_RUN", "1") == "1"

# Global flag for graceful shutdown
STOP_REQUESTED = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global STOP_REQUESTED
    logger.info("Received shutdown signal, stopping gracefully...")
    STOP_REQUESTED = True


def register_event_hooks():
    """Register AutoResearch hooks with the event bus if available."""
    if not EVENT_BUS_AVAILABLE:
        logger.warning("Event bus not available, skipping hook registration")
        return

    try:
        bus = get_bus()

        def on_task_finish(event):
            """Trigger AutoResearch after a task finishes (if enabled)."""
            if not ENABLED:
                return None

            # Only trigger for certain task types
            task_type = event.payload.get("type", "")
            if task_type not in ("build", "plan", "review"):
                return None

            logger.info(f"Task finished, triggering AutoResearch cycle: {task_type}")
            # Run in background to avoid blocking event bus
            import threading

            thread = threading.Thread(
                target=run_research_cycle, kwargs={"dry_run": DRY_RUN_DEFAULT}
            )
            thread.daemon = True
            thread.start()
            return None

        bus.register_event_listener(EventType.TASK, on_task_finish)
        logger.info("Registered AutoResearch event listener")
    except Exception as e:
        logger.warning(f"Failed to register event hooks: {e}")


def run_research_cycle(dry_run: bool = True) -> ResearchResult:
    """Run a single AutoResearch cycle and return results."""
    try:
        logger.info(f"Starting AutoResearch cycle (dry_run={dry_run})")
        engine = AutoResearchEngine(dry_run=dry_run)
        result = engine.run_cycle()
        logger.info(f"AutoResearch cycle completed: {result.summary}")
        return result
    except Exception as e:
        logger.error(f"AutoResearch cycle failed: {e}", exc_info=True)
        raise


def write_recommendation_card(result: ResearchResult, output_dir: Path):
    """Convert research recommendations to AI plan compatible cards."""
    card_dir = output_dir / "recommendation_cards"
    card_dir.mkdir(parents=True, exist_ok=True)

    cards = []
    for rec in result.recommendations:
        card = {
            "id": f"autoresearch-{rec.id}",
            "title": rec.title,
            "description": rec.description,
            "type": "recommendation",
            "risk_level": rec.risk_level.value,
            "confidence": rec.confidence,
            "requires_manual_confirmation": rec.requires_manual_confirmation,
            "target": rec.target,
            "action_type": rec.action_type,
            "expected_benefit": rec.expected_benefit,
            "generated_at": datetime.now().isoformat(),
            "research_cycle_id": result.cycle_id,
            "metadata": {
                "dependencies": rec.dependencies,
                "evidence": (
                    [f.location for f in result.findings if f.id in rec.dependencies]
                    if rec.dependencies
                    else []
                ),
            },
        }
        cards.append(card)

        # Write individual card
        card_path = card_dir / f"{card['id']}.json"
        with open(card_path, "w") as f:
            json.dump(card, f, indent=2, default=str)

    # Write summary
    summary_path = output_dir / f"{result.cycle_id}_recommendations.json"
    with open(summary_path, "w") as f:
        json.dump(
            {
                "cycle_id": result.cycle_id,
                "timestamp": result.timestamp,
                "total_recommendations": len(cards),
                "cards": cards,
            },
            f,
            indent=2,
            default=str,
        )

    logger.info(f"Wrote {len(cards)} recommendation cards to {card_dir}")
    return cards


def daemon_mode():
    """Run AutoResearch as a daemon, polling periodically."""
    if not ENABLED:
        logger.warning("AutoResearch is disabled (ATHENA_AUTORESEARCH_ENABLED != 1)")
        logger.warning("Running one cycle for verification, then exiting")
        try:
            run_research_cycle(dry_run=True)
        except Exception as e:
            logger.error(f"Verification cycle failed: {e}")
        return 0

    # Register event hooks if available
    register_event_hooks()

    logger.info("Starting AutoResearch daemon")
    logger.info(f"Polling interval: {POLL_SECONDS} seconds")
    logger.info(f"Dry-run mode: {DRY_RUN_DEFAULT}")

    cycle_count = 0
    while not STOP_REQUESTED:
        try:
            result = run_research_cycle(dry_run=DRY_RUN_DEFAULT)
            # Convert recommendations to cards
            output_dir = RUNTIME_ROOT / "workspace" / "autoresearch"
            write_recommendation_card(result, output_dir)
            cycle_count += 1
        except Exception as e:
            logger.error(f"AutoResearch daemon cycle failed: {e}")

        # Sleep until next cycle or shutdown
        for _ in range(POLL_SECONDS):
            if STOP_REQUESTED:
                break
            time.sleep(1)

    logger.info(f"AutoResearch daemon stopped after {cycle_count} cycles")
    return 0


def run_once_mode(dry_run: bool = True):
    """Run a single AutoResearch cycle and exit."""
    try:
        result = run_research_cycle(dry_run=dry_run)
        # Convert recommendations to cards
        output_dir = RUNTIME_ROOT / "workspace" / "autoresearch"
        write_recommendation_card(result, output_dir)
        print(f"\nAutoResearch cycle {result.cycle_id} completed successfully")
        print(f"Findings: {len(result.findings)}")
        print(f"Recommendations: {len(result.recommendations)}")
        print(f"Output written to: {output_dir}")
        return 0
    except Exception as e:
        logger.error(f"AutoResearch cycle failed: {e}", exc_info=True)
        return 1


def status_mode():
    """Show AutoResearch status."""
    output_dir = RUNTIME_ROOT / "workspace" / "autoresearch"
    cards_dir = output_dir / "recommendation_cards"

    print("AutoResearch Status")
    print("=" * 60)
    print(f"Enabled: {ENABLED}")
    print(f"Dry-run default: {DRY_RUN_DEFAULT}")
    print(f"Event bus available: {EVENT_BUS_AVAILABLE}")
    print(f"Output directory: {output_dir}")
    print(
        f"Recommendation cards: {len(list(cards_dir.glob('*.json')))}"
        if cards_dir.exists()
        else "0"
    )
    print()

    # List recent cycles
    cycles = list(output_dir.glob("*.json"))
    if cycles:
        print("Recent research cycles:")
        for cycle in sorted(cycles, key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            mtime = datetime.fromtimestamp(cycle.stat().st_mtime)
            print(f"  {cycle.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    else:
        print("No research cycles found.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Athena AutoResearch Runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="daemon",
        choices=["daemon", "run-once", "status", "hook-test"],
        help="Command to execute: daemon (default), run-once, status, hook-test",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DRY_RUN_DEFAULT,
        help="Run in dry-run mode (default: True)",
    )
    parser.add_argument(
        "--apply",
        action="store_false",
        dest="dry_run",
        help="Apply recommendations (disable dry-run)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.command == "daemon":
        return daemon_mode()
    elif args.command == "run-once":
        return run_once_mode(dry_run=args.dry_run)
    elif args.command == "status":
        return status_mode()
    elif args.command == "hook-test":
        logger.info("Testing event hook registration...")
        register_event_hooks()
        logger.info("Hook test completed")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
