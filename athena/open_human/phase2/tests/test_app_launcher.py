"""
Test App Launcher for Phase 2

测试 Phase 2 App 启动器功能。
使用 pytest，确保不依赖真实设备。
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from athena.open_human.phase2.actions.app_launcher import (
    AppLauncher,
    AppLaunchResult,
    LaunchResultCode,
    launch_app,
)


class TestAppLauncher:
    """测试 App 启动器"""

    def setup_method(self):
        """设置测试环境"""
        self.app_package = "com.example.app"
        self.launcher = AppLauncher()
        # Mock ADB 相关方法
        self.launcher._run_adb_command = MagicMock()
        self.launcher._get_current_package = MagicMock()
        self.launcher._launch_app_via_adb = MagicMock()

    def test_dry_run_mode_success(self):
        """测试 dry_run 模式成功"""
        result = self.launcher.launch(self.app_package, dry_run=True)

        assert result.success is True
        assert result.current_package == self.app_package
        assert result.reason == "Mock launch successful in dry-run mode"
        assert result.result_code == LaunchResultCode.SUCCESS
        assert len(result.evidence) > 0
        # 检查证据包含 dry run 信息
        assert any("Dry run mode" in ev for ev in result.evidence)
        assert any("Mock: Successfully launched app" in ev for ev in result.evidence)

    def test_empty_package_failure(self):
        """测试空包名失败"""
        result = self.launcher.launch("", dry_run=False)

        assert result.success is False
        assert result.current_package == ""
        assert "App package cannot be empty" in result.reason
        assert result.result_code == LaunchResultCode.EMPTY_PACKAGE
        assert len(result.evidence) > 0
        assert any("App package is empty" in ev for ev in result.evidence)

        # 测试空格包名
        result2 = self.launcher.launch("   ", dry_run=False)
        assert result2.success is False
        assert result2.result_code == LaunchResultCode.EMPTY_PACKAGE

    @patch("subprocess.run")
    def test_current_package_mismatch_failure(self, mock_subprocess):
        """测试当前包名不匹配失败"""
        # Mock 启动成功
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Activity started"
        mock_subprocess.return_value.stderr = ""

        # Mock 获取当前包名返回不同的包名
        self.launcher._get_current_package.return_value = (True, "com.other.app")
        self.launcher._launch_app_via_adb.return_value = (True, "App launched")

        result = self.launcher.launch(self.app_package, dry_run=False)

        assert result.success is False
        assert result.current_package == "com.other.app"
        assert "Package mismatch" in result.reason
        assert result.result_code == LaunchResultCode.PACKAGE_MISMATCH
        assert len(result.evidence) > 0
        assert any("Package mismatch" in ev for ev in result.evidence)
        assert any("expected" in ev.lower() for ev in result.evidence)
        assert any("got" in ev.lower() for ev in result.evidence)

    @patch("subprocess.run")
    def test_launch_exception_failure(self, mock_subprocess):
        """测试启动异常失败"""
        mock_subprocess.side_effect = Exception("ADB connection failed")

        result = self.launcher.launch(self.app_package, dry_run=False)

        assert result.success is False
        assert result.result_code == LaunchResultCode.UNKNOWN_ERROR
        assert "Exception during app launch" in result.reason
        assert len(result.evidence) > 0
        assert any("Exception" in ev for ev in result.evidence)

    @patch("subprocess.run")
    def test_launch_command_failure(self, mock_subprocess):
        """测试启动命令失败"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error: Activity not found"

        # Mock 获取当前包名
        self.launcher._get_current_package.return_value = (True, "com.home.app")
        # Mock 启动失败
        self.launcher._launch_app_via_adb.return_value = (False, "Error: Activity not found")

        result = self.launcher.launch(self.app_package, dry_run=False)

        assert result.success is False
        assert result.result_code == LaunchResultCode.LAUNCH_FAILED
        assert "Failed to launch app" in result.reason
        assert len(result.evidence) > 0
        assert any("Launch failed" in ev for ev in result.evidence)

    @patch("subprocess.run")
    def test_current_package_check_failure(self, mock_subprocess):
        """测试获取当前包名失败"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Activity started"

        # Mock 启动成功，但获取当前包名失败
        self.launcher._get_current_package.return_value = (False, "")
        self.launcher._launch_app_via_adb.return_value = (True, "App launched")

        result = self.launcher.launch(self.app_package, dry_run=False)

        assert result.success is False
        assert result.result_code == LaunchResultCode.CURRENT_PACKAGE_CHECK_FAILED
        assert "Failed to verify current package" in result.reason
        assert len(result.evidence) > 0
        assert any("Failed to get current package" in ev for ev in result.evidence)

    @patch("subprocess.run")
    def test_successful_launch(self, mock_subprocess):
        """测试成功启动"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Activity started"

        # Mock 启动成功，获取当前包名匹配
        self.launcher._get_current_package.return_value = (True, self.app_package)
        self.launcher._launch_app_via_adb.return_value = (True, "App launched via am start")

        result = self.launcher.launch(self.app_package, dry_run=False)

        assert result.success is True
        assert result.current_package == self.app_package
        assert result.result_code == LaunchResultCode.SUCCESS
        assert "Successfully launched" in result.reason
        assert len(result.evidence) > 0
        assert any("Successfully launched" in ev for ev in result.evidence)
        assert any("Current package after launch" in ev for ev in result.evidence)

    def test_result_structure_complete(self):
        """测试返回结构完整"""
        result = AppLaunchResult(
            success=True,
            current_package=self.app_package,
            reason="Test reason",
            evidence=["evidence1", "evidence2"],
            result_code=LaunchResultCode.SUCCESS,
        )

        assert hasattr(result, "success")
        assert hasattr(result, "current_package")
        assert hasattr(result, "reason")
        assert hasattr(result, "evidence")
        assert hasattr(result, "result_code")
        assert isinstance(result.evidence, list)
        assert len(result.evidence) == 2

    def test_evidence_not_empty_in_success(self):
        """测试成功时证据非空"""
        result = self.launcher.launch(self.app_package, dry_run=True)

        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

    def test_evidence_not_empty_in_failure(self):
        """测试失败时证据非空"""
        result = self.launcher.launch("", dry_run=False)

        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

    def test_convenience_function(self):
        """测试便捷函数 launch_app"""
        with patch("athena.open_human.phase2.actions.app_launcher.AppLauncher") as MockLauncher:
            mock_instance = MagicMock()
            mock_instance.launch.return_value = AppLaunchResult(
                success=True,
                current_package=self.app_package,
                reason="Mocked",
                evidence=["test"],
                result_code=LaunchResultCode.SUCCESS,
            )
            MockLauncher.return_value = mock_instance

            result = launch_app(self.app_package, dry_run=True, device_id="test_device")

            MockLauncher.assert_called_once_with(device_id="test_device")
            mock_instance.launch.assert_called_once_with(self.app_package, True)
            assert result.success is True

    def test_device_id_in_constructor(self):
        """测试设备ID在构造函数中传递"""
        launcher = AppLauncher(device_id="emulator-5554")
        assert launcher.device_id == "emulator-5554"
        assert launcher.device_id_arg == "-s emulator-5554"

        launcher2 = AppLauncher()
        assert launcher2.device_id is None
        assert launcher2.device_id_arg == ""

    @patch("subprocess.run")
    def test_adb_command_with_device_id(self, mock_subprocess):
        """测试带设备ID的ADB命令"""
        launcher = AppLauncher(device_id="emulator-5554")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "OK"

        success, output = launcher._run_adb_command("shell echo test")

        # 检查命令包含设备ID
        call_args = mock_subprocess.call_args[0][0]
        assert "-s emulator-5554" in call_args
        assert success is True
        assert output == "OK"


if __name__ == "__main__":
    # 支持直接运行测试
    pytest.main([__file__, "-v"])
