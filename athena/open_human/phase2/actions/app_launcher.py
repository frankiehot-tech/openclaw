"""
App Launcher for Phase 2 - App 启动器

实现可切换的真实启动能力，同时保持与 Phase 1 mock 兼容。
支持 dry_run 模式切换。
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LaunchResultCode(Enum):
    """启动结果代码枚举"""

    SUCCESS = "success"
    EMPTY_PACKAGE = "empty_package"
    PACKAGE_MISMATCH = "package_mismatch"
    LAUNCH_FAILED = "launch_failed"
    CURRENT_PACKAGE_CHECK_FAILED = "current_package_check_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class AppLaunchResult:
    """
    App 启动结果
    必须包含以下字段：
    - success: bool
    - current_package: str
    - reason: str
    - evidence: list[str]
    """

    success: bool
    current_package: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    result_code: LaunchResultCode = LaunchResultCode.UNKNOWN_ERROR

    def __post_init__(self):
        """初始化后处理"""
        if not self.evidence:
            self.evidence = []


class AppLauncher:
    """
    App 启动器类

    实现真实 App 启动能力，支持 dry_run 模式切换。
    优先复用 agent_system/device_control/ 中的现有能力。
    """

    def __init__(self, device_id: str | None = None):
        """
        初始化 App 启动器

        Args:
            device_id: 设备ID，如果为 None 则使用默认设备
        """
        self.device_id = device_id
        self.device_id_arg = f"-s {device_id}" if device_id else ""

    def _run_adb_command(self, command: str, timeout: int = 10) -> tuple[bool, str]:
        """
        执行 ADB 命令

        Args:
            command: ADB 命令
            timeout: 超时时间（秒）

        Returns:
            (成功标志, 输出内容)
        """
        full_command = f"adb {self.device_id_arg} {command}"
        logger.info(f"执行 ADB 命令: {full_command}")

        try:
            result = subprocess.run(
                full_command, shell=True, capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                logger.info(f"ADB 命令成功: {command}")
                return True, result.stdout.strip()
            else:
                logger.error(f"ADB 命令失败: {command}, 错误: {result.stderr}")
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"ADB 命令超时: {command}")
            return False, "Command timeout"
        except Exception as e:
            logger.error(f"ADB 命令异常: {command}, 异常: {str(e)}")
            return False, str(e)

    def _get_current_package(self) -> tuple[bool, str]:
        """
        获取当前前台应用包名

        Returns:
            (成功标志, 包名)
        """
        # 方法1: 通过 dumpsys window windows 获取
        success, output = self._run_adb_command(
            "shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
        )

        if success:
            # 解析包名
            package_pattern = r"[a-zA-Z0-9._]+/[\w.]+"
            matches = re.findall(package_pattern, output)
            if matches:
                package = matches[0].split("/")[0]
                logger.info(f"通过 mCurrentFocus 获取当前包名: {package}")
                return True, package

        # 方法2: 通过 dumpsys activity top 获取
        success2, output2 = self._run_adb_command("shell dumpsys activity top | grep ACTIVITY")
        if success2 and output2:
            # 解析输出: ACTIVITY com.example.app/.MainActivity
            for line in output2.split("\n"):
                if "ACTIVITY" in line and "/" in line:
                    parts = line.strip().split()
                    for part in parts:
                        if "/" in part and "." in part:
                            package = part.split("/")[0]
                            logger.info(f"通过 activity top 获取当前包名: {package}")
                            return True, package

        # 方法3: 简单方法获取当前包名
        success3, output3 = self._run_adb_command("shell dumpsys window | grep mCurrentFocus")
        if success3 and "=" in output3:
            match = re.search(r"[a-zA-Z0-9._]+/[\w.]+", output3)
            if match:
                package = match.group(0).split("/")[0]
                logger.info(f"通过简单方法获取当前包名: {package}")
                return True, package

        logger.warning("无法获取当前包名")
        return False, ""

    def _launch_app_via_adb(self, app_package: str) -> tuple[bool, str]:
        """
        通过 ADB 启动 App

        Args:
            app_package: App 包名

        Returns:
            (成功标志, 输出信息)
        """
        try:
            # 尝试启动应用主 Activity
            launch_command = f"shell am start -n {app_package}/.MainActivity"
            success, output = self._run_adb_command(launch_command)

            if not success:
                # 尝试不带 Activity 名称启动
                launch_command2 = (
                    f"shell monkey -p {app_package} -c android.intent.category.LAUNCHER 1"
                )
                success2, output2 = self._run_adb_command(launch_command2)
                if success2:
                    return True, "App launched via monkey command"
                return False, f"Failed to launch app: {output}"

            return True, "App launched via am start"
        except Exception as e:
            logger.error(f"Exception in _launch_app_via_adb: {str(e)}")
            return False, f"Exception during app launch: {str(e)}"

    def launch(self, app_package: str, dry_run: bool = False) -> AppLaunchResult:
        """
        启动 App

        Args:
            app_package: App 包名
            dry_run: 是否为 dry-run 模式

        Returns:
            AppLaunchResult 结果对象

        规则:
        1. dry_run=True 时，允许返回受控 mock 成功结果
        2. dry_run=False 时，优先调用现有真实 app 启动能力
        3. 启动后必须尝试确认 current_package
        4. 若 current_package != app_package，则不得判 success
        5. app_package 为空时必须直接失败
        6. 启动异常时 success=False，reason 可解释
        7. evidence 必须记录启动命令、包名确认结果或异常信息
        """
        evidence = []

        # 规则5: app_package 为空时必须直接失败
        if not app_package or not app_package.strip():
            evidence.append("App package is empty")
            return AppLaunchResult(
                success=False,
                current_package="",
                reason="App package cannot be empty",
                evidence=evidence,
                result_code=LaunchResultCode.EMPTY_PACKAGE,
            )

        logger.info(f"开始启动 App: {app_package}, dry_run={dry_run}")
        evidence.append(f"Target app package: {app_package}")
        evidence.append(f"Dry run mode: {dry_run}")

        if dry_run:
            # dry_run 模式：返回受控 mock 成功结果
            evidence.append("Dry run mode: Using mock launch result")
            evidence.append("Mock: Successfully launched app (dry run)")
            evidence.append("Mock: Current package matches target (dry run)")

            return AppLaunchResult(
                success=True,
                current_package=app_package,
                reason="Mock launch successful in dry-run mode",
                evidence=evidence,
                result_code=LaunchResultCode.SUCCESS,
            )

        # 真实启动模式
        try:
            # 启动前获取当前包名（用于对比）
            evidence.append("Getting current package before launch...")
            before_success, before_package = self._get_current_package()
            if before_success:
                evidence.append(f"Current package before launch: {before_package}")
            else:
                evidence.append("Failed to get current package before launch")

            # 启动 App
            evidence.append(f"Launching app: {app_package}")
            launch_success, launch_output = self._launch_app_via_adb(app_package)
            evidence.append(f"Launch command output: {launch_output}")

            if not launch_success:
                evidence.append(f"Launch failed: {launch_output}")
                return AppLaunchResult(
                    success=False,
                    current_package=before_package if before_success else "",
                    reason=f"Failed to launch app: {launch_output}",
                    evidence=evidence,
                    result_code=LaunchResultCode.LAUNCH_FAILED,
                )

            # 等待一段时间让应用完全启动
            import time

            time.sleep(2)  # 等待2秒

            # 启动后获取当前包名
            evidence.append("Getting current package after launch...")
            after_success, after_package = self._get_current_package()

            if not after_success:
                evidence.append("Failed to get current package after launch")
                return AppLaunchResult(
                    success=False,
                    current_package="",
                    reason="Failed to verify current package after launch",
                    evidence=evidence,
                    result_code=LaunchResultCode.CURRENT_PACKAGE_CHECK_FAILED,
                )

            evidence.append(f"Current package after launch: {after_package}")

            # 规则4: 若 current_package != app_package，则不得判 success
            if after_package != app_package:
                evidence.append(f"Package mismatch: expected {app_package}, got {after_package}")
                return AppLaunchResult(
                    success=False,
                    current_package=after_package,
                    reason=f"Package mismatch after launch: expected {app_package}, got {after_package}",
                    evidence=evidence,
                    result_code=LaunchResultCode.PACKAGE_MISMATCH,
                )

            # 成功启动且包名匹配
            evidence.append(f"Successfully launched {app_package}")
            return AppLaunchResult(
                success=True,
                current_package=after_package,
                reason=f"Successfully launched {app_package}",
                evidence=evidence,
                result_code=LaunchResultCode.SUCCESS,
            )

        except Exception as e:
            # 规则6: 启动异常时 success=False，reason 可解释
            error_msg = f"Exception during app launch: {str(e)}"
            logger.error(error_msg)
            evidence.append(f"Exception: {error_msg}")

            return AppLaunchResult(
                success=False,
                current_package="",
                reason=error_msg,
                evidence=evidence,
                result_code=LaunchResultCode.UNKNOWN_ERROR,
            )


# 便捷函数
def launch_app(
    app_package: str, dry_run: bool = False, device_id: str | None = None
) -> AppLaunchResult:
    """
    便捷函数：启动 App

    Args:
        app_package: App 包名
        dry_run: 是否为 dry-run 模式
        device_id: 设备ID

    Returns:
        AppLaunchResult 结果对象
    """
    launcher = AppLauncher(device_id=device_id)
    return launcher.launch(app_package, dry_run)


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=== App Launcher 测试 ===")

    if len(sys.argv) < 2:
        print("用法: python app_launcher.py <app_package> [--dry-run]")
        print("示例: python app_launcher.py com.example.app --dry-run")
        sys.exit(1)

    app_package = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    print(f"测试启动: {app_package}, dry_run={dry_run}")

    result = launch_app(app_package, dry_run=dry_run)

    print(f"成功: {result.success}")
    print(f"当前包名: {result.current_package}")
    print(f"原因: {result.reason}")
    print(f"结果代码: {result.result_code}")
    print("证据:")
    for i, ev in enumerate(result.evidence, 1):
        print(f"  {i}. {ev}")
