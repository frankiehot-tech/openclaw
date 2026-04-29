#!/usr/bin/env python3
"""Test AutoResearch constraint gates.

Validates that constraint gates properly reject invalid recommendations
and allow valid ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from athena_autoresearch_engine import (
    ConstraintGate,
    ConstraintViolation,
    Recommendation,
    RiskLevel,
)


def test_constraint_gate() -> None:
    """Run constraint gate tests."""
    print("Testing AutoResearch constraint gates...")

    gate = ConstraintGate()
    passed = 0
    failed = 0

    # Test 1: Valid target (scripts directory)
    print("\n1. Testing valid target (scripts/):")
    try:
        gate.validate_target("scripts/test_autoresearch_constraints.py")
        print("   PASS: Valid target accepted")
        passed += 1
    except ConstraintViolation as e:
        print(f"   FAIL: {e}")
        failed += 1

    # Test 2: Forbidden target (.openclaw/)
    print("\n2. Testing forbidden target (.openclaw/):")
    try:
        gate.validate_target(".openclaw/orchestrator/tasks.json")
        print("   FAIL: Forbidden target was accepted")
        failed += 1
    except ConstraintViolation as e:
        print(f"   PASS: Forbidden target rejected: {e}")
        passed += 1

    # Test 3: Target outside runtime root
    print("\n3. Testing target outside runtime root:")
    try:
        gate.validate_target("/tmp/somefile.py")
        print("   FAIL: External target was accepted")
        failed += 1
    except ConstraintViolation as e:
        print(f"   PASS: External target rejected: {e}")
        passed += 1

    # Test 4: Valid root-level .md file
    print("\n4. Testing valid root-level .md file:")
    try:
        gate.validate_target("README.md")
        print("   PASS: Root-level .md file accepted")
        passed += 1
    except ConstraintViolation as e:
        print(f"   FAIL: {e}")
        failed += 1

    # Test 5: High-risk action detection
    print("\n5. Testing high-risk action detection:")
    rec = Recommendation(
        id="test-rec-1",
        title="Delete old logs",
        description="Delete old log files to save space",
        action_type="delete_file",  # High-risk action
        target="workspace/old_logs.txt",
        expected_benefit="Save disk space",
        risk_level=RiskLevel.MEDIUM,
        confidence=0.8,
        dependencies=[],
        requires_manual_confirmation=False,  # Should be forced to True
    )

    is_valid, warnings = gate.validate_recommendation(rec)
    if is_valid:
        print("   PASS: Recommendation validated")
        if rec.requires_manual_confirmation:
            print("   PASS: High-risk action requires manual confirmation")
        else:
            print("   FAIL: High-risk action should require manual confirmation")
            failed += 1
        passed += 1
    else:
        print(f"   FAIL: Valid recommendation rejected: {warnings}")
        failed += 1

    # Test 6: Low confidence with high risk
    print("\n6. Testing low confidence with high risk:")
    rec2 = Recommendation(
        id="test-rec-2",
        title="Modify core config",
        description="Change core configuration parameter",
        action_type="config_change",
        target="scripts/athena_ai_plan_runner.py",
        expected_benefit="Improve performance",
        risk_level=RiskLevel.HIGH,
        confidence=0.5,  # Low confidence
        dependencies=[],
        requires_manual_confirmation=False,
    )

    is_valid, warnings = gate.validate_recommendation(rec2)
    if is_valid:
        print("   PASS: Recommendation validated")
        if rec2.requires_manual_confirmation:
            print("   PASS: Low confidence high-risk requires manual confirmation")
        else:
            print("   FAIL: Should require manual confirmation")
            failed += 1
        passed += 1
    else:
        print(f"   FAIL: Valid recommendation rejected: {warnings}")
        failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("Constraint Gate Test Results:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")

    if failed == 0:
        print("\nAll tests passed! Constraint gates are working correctly.")
    else:
        print(f"\n{failed} tests failed. Please review constraint logic.")
        sys.exit(1)


def test_dry_run_behavior() -> None:
    """Test that dry-run mode adds manual confirmation requirements."""
    print("\n" + "=" * 60)
    print("Testing dry-run behavior...")

    from athena_autoresearch_engine import AutoResearchEngine

    # Create engine in dry-run mode
    engine = AutoResearchEngine(dry_run=True)

    # Create a simple recommendation
    rec = Recommendation(
        id="dry-run-test",
        title="Test recommendation",
        description="Test description",
        action_type="code_refactor",
        target="scripts/test.py",
        expected_benefit="Test benefit",
        risk_level=RiskLevel.LOW,
        confidence=0.9,
        dependencies=[],
        requires_manual_confirmation=False,
    )

    # Apply gates (should add dry-run prefix and require confirmation)
    approved, warnings = engine.gate([rec])

    if approved:
        approved_rec = approved[0]
        if approved_rec.requires_manual_confirmation:
            print("PASS: Dry-run mode requires manual confirmation")
        else:
            print("FAIL: Dry-run should require manual confirmation")

        if approved_rec.title.startswith("[DRY-RUN]"):
            print("PASS: Dry-run prefix added to title")
        else:
            print("FAIL: Dry-run prefix not added to title")
    else:
        print("FAIL: Recommendation was not approved in dry-run mode")

    print("Dry-run behavior test completed.")


if __name__ == "__main__":
    test_constraint_gate()
    test_dry_run_behavior()
