#!/usr/bin/env python3
"""
Software Executor - 软件/网页执行器抽象层

支持两种 provider 状态：
- opencli: 当前优先 provider，真实可用
- cli_anything: 可选 provider，只做检测、声明、接入口预留
"""

import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider 状态"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    OPTIONAL = "optional"
    GATED = "gated"
    UNKNOWN = "unknown"


@dataclass
class ProviderCapability:
    """Provider 能力"""

    name: str
    description: str
    supported_actions: List[str]
    limitations: List[str]


@dataclass
class ProviderInfo:
    """Provider 信息"""

    id: str
    name: str
    status: str
    detection_command: str
    check_command: str
    capabilities: List[Dict]
    installation_guide: str
    notes: str

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class SoftwareExecutor:
    """软件执行器管理器"""

    def __init__(self):
        self.providers = self._initialize_providers()
        self.detect_providers()

    def _initialize_providers(self) -> Dict[str, ProviderInfo]:
        """初始化 provider 配置"""
        return {
            "opencli": ProviderInfo(
                id="opencli",
                name="OpenCLI",
                status=ProviderStatus.UNKNOWN.value,
                detection_command="which opencli",
                check_command="opencli --version",
                capabilities=[
                    {
                        "name": "web_browsing",
                        "description": "网页只读扫描",
                        "supported_actions": ["scan", "extract", "navigate"],
                        "limitations": ["只读", "需要网络连接"],
                    },
                    {
                        "name": "command_execution",
                        "description": "命令行透传",
                        "supported_actions": ["run", "pipe", "capture"],
                        "limitations": ["需人工审核高风险命令"],
                    },
                ],
                installation_guide="brew install opencli 或参考 https://github.com/jackwener/opencli",
                notes="当前优先 provider，真实可用",
            ),
            "cli_anything": ProviderInfo(
                id="cli_anything",
                name="CLI-Anything",
                status=ProviderStatus.OPTIONAL.value,
                detection_command="which cli-anything",
                check_command="cli-anything --version",
                capabilities=[
                    {
                        "name": "software_automation",
                        "description": "软件自动化 CLI 生成",
                        "supported_actions": ["generate", "execute", "monitor"],
                        "limitations": ["需特定软件支持", "需配置环境"],
                    },
                    {
                        "name": "browser_control",
                        "description": "浏览器控制增强",
                        "supported_actions": ["automate", "script", "record"],
                        "limitations": ["需浏览器扩展", "需人工监督"],
                    },
                ],
                installation_guide="参考 https://github.com/HKUDS/CLI-Anything",
                notes="可选 provider，只做检测、声明、接入口预留",
            ),
        }

    def detect_providers(self) -> Dict[str, ProviderStatus]:
        """检测 provider 可用性"""
        results = {}
        for provider_id, provider in self.providers.items():
            # 执行检测命令
            try:
                result = subprocess.run(
                    provider.detection_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                detected = result.returncode == 0
            except Exception as e:
                logger.warning(f"检测 {provider_id} 时出错: {e}")
                detected = False

            # 更新状态
            if detected:
                # 进一步检查是否可运行
                try:
                    subprocess.run(
                        provider.check_command,
                        shell=True,
                        capture_output=True,
                        timeout=5,
                    )
                    provider.status = ProviderStatus.AVAILABLE.value
                except Exception:
                    provider.status = ProviderStatus.GATED.value
            else:
                if provider.status == ProviderStatus.OPTIONAL.value:
                    # 保持 optional 状态（未安装但可选）
                    pass
                else:
                    provider.status = ProviderStatus.UNAVAILABLE.value

            results[provider_id] = ProviderStatus(provider.status)

        return results

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """获取 provider 信息"""
        return self.providers.get(provider_id)

    def list_providers(self) -> List[Dict]:
        """列出所有 provider 信息"""
        return [provider.to_dict() for provider in self.providers.values()]

    def get_available_providers(self) -> List[Dict]:
        """获取可用 provider 列表"""
        available = []
        for provider in self.providers.values():
            if provider.status in [
                ProviderStatus.AVAILABLE.value,
                ProviderStatus.OPTIONAL.value,
            ]:
                available.append(provider.to_dict())
        return available

    def execute_with_provider(
        self, provider_id: str, command: str, args: Optional[Dict] = None
    ) -> Dict:
        """
        使用指定 provider 执行命令

        Args:
            provider_id: provider ID
            command: 命令或动作
            args: 参数字典

        Returns:
            执行结果
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return {
                "success": False,
                "error": f"Provider 不存在: {provider_id}",
                "provider_id": provider_id,
            }

        # 检查状态
        if provider.status not in [
            ProviderStatus.AVAILABLE.value,
            ProviderStatus.OPTIONAL.value,
        ]:
            return {
                "success": False,
                "error": f"Provider 不可用: {provider_id} (状态: {provider.status})",
                "provider_id": provider_id,
                "status": provider.status,
                "notes": provider.notes,
            }

        # 实际执行逻辑（根据 provider 类型）
        if provider_id == "opencli":
            return self._execute_opencli(command, args)
        elif provider_id == "cli_anything":
            return self._execute_cli_anything(command, args)
        else:
            return {
                "success": False,
                "error": f"未实现的 provider: {provider_id}",
                "provider_id": provider_id,
            }

    def _execute_opencli(self, command: str, args: Optional[Dict]) -> Dict:
        """执行 opencli 命令"""
        # 构建命令字符串
        cmd_parts = ["opencli"]
        if command:
            cmd_parts.append(command)

        if args:
            for key, value in args.items():
                if isinstance(value, bool) and value:
                    cmd_parts.append(f"--{key}")
                elif not isinstance(value, bool):
                    cmd_parts.append(f"--{key}")
                    cmd_parts.append(str(value))

        full_command = " ".join(cmd_parts)

        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return {
                "success": result.returncode == 0,
                "provider": "opencli",
                "command": full_command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "executed": True,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "执行超时",
                "provider": "opencli",
                "command": full_command,
                "executed": False,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "opencli",
                "command": full_command,
                "executed": False,
            }

    def _execute_cli_anything(self, command: str, args: Optional[Dict]) -> Dict:
        """执行 cli_anything 命令（模拟/预留）"""
        # 目前只返回预留接口信息
        return {
            "success": True,
            "executed": False,
            "provider": "cli_anything",
            "message": "CLI-Anything 目前仅为预留接口，未实际安装或集成",
            "integration_status": "optional",
            "installation_guide": self.providers["cli_anything"].installation_guide,
            "notes": self.providers["cli_anything"].notes,
            "command": command,
            "args": args,
        }

    def get_status_report(self) -> Dict:
        """获取状态报告"""
        self.detect_providers()

        report = {
            "timestamp": self._current_timestamp(),
            "providers": {},
            "summary": {
                "total": len(self.providers),
                "available": 0,
                "unavailable": 0,
                "optional": 0,
            },
        }

        for provider_id, provider in self.providers.items():
            report["providers"][provider_id] = provider.to_dict()

            if provider.status == ProviderStatus.AVAILABLE.value:
                report["summary"]["available"] += 1
            elif provider.status == ProviderStatus.UNAVAILABLE.value:
                report["summary"]["unavailable"] += 1
            elif provider.status == ProviderStatus.OPTIONAL.value:
                report["summary"]["optional"] += 1

        return report

    def _current_timestamp(self) -> str:
        """获取当前时间戳"""
        import time

        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 全局执行器实例
_executor_instance: Optional[SoftwareExecutor] = None


def get_executor() -> SoftwareExecutor:
    """获取全局执行器实例"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SoftwareExecutor()
    return _executor_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Software Executor 测试 ===")

    executor = SoftwareExecutor()

    print("\n1. Provider 检测结果:")
    for provider_id, provider in executor.providers.items():
        print(f"  {provider.name} ({provider_id}): {provider.status}")

    print("\n2. 可用 provider 列表:")
    available = executor.get_available_providers()
    for provider in available:
        print(f"  {provider['name']} - 状态: {provider['status']}")

    print("\n3. 状态报告:")
    report = executor.get_status_report()
    print(f"  总计: {report['summary']['total']}")
    print(f"  可用: {report['summary']['available']}")
    print(f"  不可用: {report['summary']['unavailable']}")
    print(f"  可选: {report['summary']['optional']}")

    print("\n4. 测试 opencli 执行（如果可用）:")
    opencli_provider = executor.get_provider("opencli")
    if opencli_provider and opencli_provider.status == ProviderStatus.AVAILABLE.value:
        print("  OpenCLI 可用，测试简单命令...")
        result = executor.execute_with_provider("opencli", "--help")
        print(f"  成功: {result.get('success', False)}")
        if result.get("stdout"):
            print(f"  输出长度: {len(result['stdout'])} 字符")
    else:
        print("  OpenCLI 不可用，跳过执行测试")

    print("\n5. 测试 CLI-Anything 预留接口:")
    result = executor.execute_with_provider(
        "cli_anything",
        "generate",
        {"target": "chrome", "action": "click"},
    )
    print(f"  成功: {result.get('success', False)}")
    print(f"  消息: {result.get('message', 'N/A')}")

    print("\n✅ Software Executor 测试完成")
