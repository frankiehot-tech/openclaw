"""Tests for scripts/runner/utils.py — pure utility functions"""

from scripts.runner.utils import clip, now_iso, slugify


class TestSlugify:
    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("foo/bar baz!") == "foo-bar-baz"

    def test_multiple_hyphens(self):
        assert slugify("a---b") == "a-b"

    def test_strip_leading_trailing(self):
        assert slugify("-hello-") == "hello"

    def test_chinese_chars(self):
        result = slugify("你好世界")
        assert result == "task"  # falls back when no ASCII chars remain

    def test_empty_string(self):
        assert slugify("") == "task"

    def test_only_special_chars(self):
        assert slugify("!!!") == "task"


class TestClip:
    def test_short_text(self):
        assert clip("hello", limit=10) == "hello"

    def test_exact_limit(self):
        text = "a" * 10
        assert clip(text, limit=10) == text

    def test_truncate(self):
        text = "a" * 20
        result = clip(text, limit=10)
        assert len(result) == 10
        assert result.endswith("…")

    def test_ansi_stripped(self):
        text = "\x1b[31mhello\x1b[0m world"
        assert clip(text, limit=20) == "hello world"

    def test_default_limit(self):
        text = "a" * 300
        result = clip(text)
        assert len(result) <= 240

    def test_none_value(self):
        assert clip(None) == ""

    def test_int_value(self):
        assert clip(42) == "42"


class TestNowIso:
    def test_returns_string(self):
        result = now_iso()
        assert isinstance(result, str)

    def test_iso_format(self):
        result = now_iso()
        # Should match ISO 8601 with timezone: e.g. 2026-04-27T12:34:56+08:00
        assert "T" in result
        assert "+" in result or result.endswith("Z")

    def test_seconds_precision(self):
        result = now_iso()
        # No microseconds
        assert "." not in result.split("+")[0].split("-")[-1]
