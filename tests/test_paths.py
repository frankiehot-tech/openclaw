"""Tests for config/paths.py — centralized path management."""

from pathlib import Path

from config.paths import (
    CONFIG_DIR,
    DOCS_DIR,
    LOGS_DIR,
    OPENCLAW_DIR,
    PLAN_QUEUE_DIR,
    QUEUE_FILES,
    ROOT_DIR,
    SCRIPTS_DIR,
    detect_environment,
    get_all_queue_files,
    get_latest_queue_file,
    get_queue_file,
    validate_paths,
)


class TestPathConstants:
    def test_root_dir_is_path(self):
        assert isinstance(ROOT_DIR, Path)

    def test_root_dir_exists(self):
        assert ROOT_DIR.exists()

    def test_openclaw_dir_is_subdir(self):
        assert OPENCLAW_DIR == ROOT_DIR / ".openclaw"

    def test_plan_queue_dir_resolved(self):
        assert PLAN_QUEUE_DIR == OPENCLAW_DIR / "plan_queue"

    def test_scripts_dir_resolved(self):
        assert SCRIPTS_DIR == ROOT_DIR / "scripts"

    def test_config_dir_resolved(self):
        assert CONFIG_DIR == ROOT_DIR / "config"

    def test_logs_dir_resolved(self):
        assert LOGS_DIR == ROOT_DIR / "logs"

    def test_docs_dir_resolved(self):
        assert DOCS_DIR == ROOT_DIR / "docs"

    def test_queue_files_is_dict(self):
        assert isinstance(QUEUE_FILES, dict)

    def test_queue_files_has_expected_keys(self):
        expected = {"plan_manual", "build_priority", "review_priority", "qa_priority", "priority_execution", "gene_management"}
        assert set(QUEUE_FILES.keys()) == expected

    def test_queue_files_values_are_paths(self):
        for v in QUEUE_FILES.values():
            assert isinstance(v, Path)


class TestDetectEnvironment:
    def test_default_development(self):
        env = detect_environment()
        assert env in ("development", "testing", "production")

    def test_returns_string(self):
        assert isinstance(detect_environment(), str)


class TestGetQueueFile:
    def test_known_key(self):
        result = get_queue_file("plan_manual")
        assert result is not None
        assert isinstance(result, Path)

    def test_unknown_key(self):
        assert get_queue_file("nonexistent_queue_xyz") is None


class TestGetAllQueueFiles:
    def test_returns_list(self):
        files = get_all_queue_files()
        assert isinstance(files, list)

    def test_entries_are_paths(self):
        files = get_all_queue_files()
        if files:
            assert all(isinstance(f, Path) for f in files)

    def test_all_exist(self):
        files = get_all_queue_files()
        if files:
            assert all(f.exists() for f in files)


class TestGetLatestQueueFile:
    def test_returns_none_for_bad_pattern(self):
        assert get_latest_queue_file("zzz_no_match_99999") is None

    def test_returns_path_or_none(self):
        result = get_latest_queue_file()
        assert result is None or isinstance(result, Path)


class TestValidatePaths:
    def test_returns_dict(self):
        result = validate_paths()
        assert isinstance(result, dict)

    def test_contains_expected_keys(self):
        result = validate_paths()
        expected_keys = {"ROOT_DIR", "OPENCLAW_DIR", "CONFIG_DIR", "SCRIPTS_DIR", "LOGS_DIR", "DOCS_DIR", "CLAUDE_CONFIG", "TASK_PLAN", "FINDINGS", "PROGRESS", "ATHENA_AI_PLAN_RUNNER"}
        for key in expected_keys:
            assert key in result

    def test_root_dir_exists_in_validation(self):
        result = validate_paths()
        assert result.get("ROOT_DIR") is True
