"""Tests for scripts/runner/config.py — configuration loading"""

from scripts.runner.config import (
    AUTO_ARCHIVE_COMPLETED,
    AUTO_RETRY_LIMIT,
    BLOCKED_RESCUE_FAILURE_MARKERS,
    BUILD_TIMEOUT_SECONDS,
    POLL_SECONDS,
    RETRYABLE_FAILURE_MARKERS,
    REVIEW_TIMEOUT_SECONDS,
)


class TestConfigDefaults:
    def test_poll_seconds_default(self):
        assert POLL_SECONDS == 15

    def test_build_timeout_default(self):
        assert BUILD_TIMEOUT_SECONDS == 1800

    def test_review_timeout_default(self):
        assert REVIEW_TIMEOUT_SECONDS == 1200

    def test_auto_retry_limit_default(self):
        assert AUTO_RETRY_LIMIT >= 0

    def test_auto_archive_default_true(self):
        assert AUTO_ARCHIVE_COMPLETED is True


class TestRetryableMarkers:
    def test_contains_network_errors(self):
        assert "Connection reset by peer" in RETRYABLE_FAILURE_MARKERS
        assert "Connection timed out" in RETRYABLE_FAILURE_MARKERS
        assert "Temporary failure in name resolution" in RETRYABLE_FAILURE_MARKERS

    def test_contains_http_errors(self):
        assert "403" in RETRYABLE_FAILURE_MARKERS
        assert "429" in RETRYABLE_FAILURE_MARKERS
        assert "502" in RETRYABLE_FAILURE_MARKERS

    def test_contains_quota_errors(self):
        assert "rate_limit_exceeded" in RETRYABLE_FAILURE_MARKERS
        assert "quota_exceeded" in RETRYABLE_FAILURE_MARKERS
        assert "billing_hard_limit_reached" in RETRYABLE_FAILURE_MARKERS


class TestBlockedRescueMarkers:
    def test_contains_blocked(self):
        assert "blocked" in BLOCKED_RESCUE_FAILURE_MARKERS
        assert "blocked_rescue" in BLOCKED_RESCUE_FAILURE_MARKERS

    def test_contains_queue_capacity(self):
        assert "Queue capacity reached" in BLOCKED_RESCUE_FAILURE_MARKERS

    def test_contains_resource_gates(self):
        assert "resource gate: memory" in BLOCKED_RESCUE_FAILURE_MARKERS
        assert "resource gate: cpu" in BLOCKED_RESCUE_FAILURE_MARKERS
