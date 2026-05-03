"""
Compliant MVP Flow for Phase 1 - 合规 MVP 主流程

将前四个子任务模块串联为单平台、单授权账号、单闭环的合规 MVP 主流程。
严格遵循 Phase 1 硬边界：
- 不实现真实发布执行器
- 不扩展到多平台、多账号、自动注册
- 只做流程控制、状态转换、守卫判定、审计记录和 dry-run 入口
"""

import json
import sys
import uuid
from dataclasses import asdict, dataclass
from typing import Any

import yaml

from athena.open_human.phase1.audit.audit_logger import (
    get_default_audit_logger,
    log_audit_event,
)
from athena.open_human.phase1.audit.audit_schema import AuditEvent

# 导入已有模块
from athena.open_human.phase1.guards.account_scope_guard import (
    AccountScopeGuard,
    check_account_scope,
)
from athena.open_human.phase1.guards.human_confirmation_guard import (
    ConfirmationDecision,
    HumanConfirmationGuard,
)
from athena.open_human.phase1.guards.pre_publish_guard import (
    PrePublishGuard,
    check_pre_publish_conditions,
)
from athena.open_human.phase1.states.page_state_classifier import (
    PageStateClassifier,
)
from athena.open_human.phase1.states.page_state_schema import Phase1PageState
from athena.open_human.phase1.templates.form_template_schema import (
    DraftFormTemplate,
)
from athena.open_human.phase1.verification.publish_result_verifier import (
    PublishResultVerifier,
    verify_publish_result,
)

# Phase 2: 导入 App 启动器
try:
    from athena.open_human.phase2.actions.app_launcher import (
        AppLauncher,
    )
    from athena.open_human.phase2.actions.app_launcher import (
        launch_app as launch_app_real,
    )

    PHASE2_APP_LAUNCHER_AVAILABLE = True
except ImportError:
    # 如果 Phase 2 模块不存在，回退到 mock
    PHASE2_APP_LAUNCHER_AVAILABLE = False

    class MockAppLauncher:
        """用于回退的 Mock App Launcher"""

        def launch(self, app_package: str, dry_run: bool = False):
            from dataclasses import dataclass, field

            @dataclass
            class MockAppLaunchResult:
                success: bool
                current_package: str
                reason: str
                evidence: list[str] = field(default_factory=list)

            return MockAppLaunchResult(
                success=True,
                current_package=app_package,
                reason="Mock launch (fallback)",
                evidence=[f"Mock launch for {app_package}", f"dry_run={dry_run}"],
            )

    AppLauncher = MockAppLauncher

    def launch_app_real(app_package: str, dry_run: bool = False, device_id: str | None = None):
        launcher = MockAppLauncher()
        return launcher.launch(app_package, dry_run)


# Phase 2: 导入创建入口导航器
try:
    from athena.open_human.phase2.navigation.create_entry_navigator import (
        CreateEntryNavigationResult        CreateEntryNavigator,
        navigate_to_create_entry,
    )

    PHASE2_CREATE_ENTRY_NAVIGATOR_AVAILABLE = True
except ImportError:
    # 如果 Phase 2 模块不存在，回退到 mock
    PHASE2_CREATE_ENTRY_NAVIGATOR_AVAILABLE = False

    class MockCreateEntryNavigator:
        """用于回退的 Mock Create Entry Navigator"""

        def navigate(
            self,
            app_package: str,
            current_package: str,
            vision_text: str,
            ui_anchors: list[str],
            dry_run: bool = False,
        ):
            from dataclasses import dataclass, field
            from enum import Enum

            class MockNavigationResultCode(Enum):
                SUCCESS = "success"
                UNKNOWN_ERROR = "unknown_error"

            @dataclass
            class MockCreateEntryNavigationResult:
                success: bool
                final_page_state: str
                reason: str
                evidence: list[str] = field(default_factory=list)
                result_code = MockNavigationResultCode.SUCCESS

            return MockCreateEntryNavigationResult(
                success=True,
                final_page_state="create_entry",
                reason="Mock navigation (fallback)",
                evidence=[
                    f"Mock navigation to create entry for {app_package}",
                    f"dry_run={dry_run}",
                ],
            )

    CreateEntryNavigator = MockCreateEntryNavigator

    def navigate_to_create_entry(
        app_package: str,
        current_package: str,
        vision_text: str,
        ui_anchors: list[str],
        dry_run: bool = False,
        device_id: str | None = None,
    ):
        navigator = MockCreateEntryNavigator()
        return navigator.navigate(app_package, current_package, vision_text, ui_anchors, dry_run)


# Phase 2: 导入草稿编辑导航器
try:
    from athena.open_human.phase2.navigation.draft_edit_navigator import (
        DraftEditNavigationResult        DraftEditNavigator,
        navigate_to_draft_edit,
    )

    PHASE2_DRAFT_EDIT_NAVIGATOR_AVAILABLE = True
except ImportError:
    # 如果 Phase 2 模块不存在，回退到 mock
    PHASE2_DRAFT_EDIT_NAVIGATOR_AVAILABLE = False

    class MockDraftEditNavigator:
        """用于回退的 Mock Draft Edit Navigator"""

        def navigate(
            self,
            app_package: str,
            current_package: str,
            vision_text: str,
            ui_anchors: list[str],
            dry_run: bool = False,
        ):
            from dataclasses import dataclass, field
            from enum import Enum

            class MockNavigationResultCode(Enum):
                SUCCESS = "success"
                UNKNOWN_ERROR = "unknown_error"

            @dataclass
            class MockDraftEditNavigationResult:
                success: bool
                final_page_state: str
                reason: str
                evidence: list[str] = field(default_factory=list)
                result_code = MockNavigationResultCode.SUCCESS

            return MockDraftEditNavigationResult(
                success=True,
                final_page_state="draft_edit",
                reason="Mock navigation (fallback)",
                evidence=[f"Mock navigation to draft edit for {app_package}", f"dry_run={dry_run}"],
            )

    DraftEditNavigator = MockDraftEditNavigator

    def navigate_to_draft_edit(
        app_package: str,
        current_package: str,
        vision_text: str,
        ui_anchors: list[str],
        dry_run: bool = False,
        device_id: str | None = None,
    ):
        navigator = MockDraftEditNavigator()
        return navigator.navigate(app_package, current_package, vision_text, ui_anchors, dry_run)


@dataclass
class CompliantMVPFlowResult:
    """
    Phase 1 合规 MVP 流程结果
    必须包含以下字段：
    - success: bool - 流程是否成功完成
    - final_status: str - 最终状态 (success / fail / safe_stop / cancelled)
    - task_id: str - 任务ID
    - sample_id: str - 样本ID
    - taxonomy_class: str | None - 分类标识（用于 fail / safe_stop）
    - sub_reason: str | None - 子原因（用于 fail / safe_stop）
    """

    success: bool
    final_status: str  # success / fail / safe_stop / cancelled
    task_id: str
    sample_id: str
    taxonomy_class: str | None = None
    sub_reason: str | None = None
    flow_steps: list[dict] | None = None
    audit_events: list[str] | None = None

    def __post_init__(self):
        """初始化后处理"""
        if self.flow_steps is None:
            self.flow_steps = []
        if self.audit_events is None:
            self.audit_events = []

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 移除可能为None的字段
        result = {k: v for k, v in result.items() if v is not None}
        return result

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class CompliantMVPFlow:
    """
    Phase 1 合规 MVP 主流程

    严格按26个步骤顺序执行，复用已有模块，记录审计事件。
    支持 dry-run 模式。
    """

    def __init__(
        self,
        platform_config_path: str,
        authorized_account_config_path: str,
        draft_template_path: str,
        draft_payload: dict[str, Any],
        dry_run: bool = True,
        task_id: str | None = None,
        sample_id: str | None = None,
    ):
        """
        初始化流程

        Args:
            platform_config_path: 平台配置路径
            authorized_account_config_path: 授权账号配置路径
            draft_template_path: 草稿模板路径
            draft_payload: 草稿内容字典
            dry_run: 是否为 dry-run 模式（默认True）
            task_id: 任务ID（如未提供则生成）
            sample_id: 样本ID（如未提供则生成）
        """
        self.platform_config_path = platform_config_path
        self.authorized_account_config_path = authorized_account_config_path
        self.draft_template_path = draft_template_path
        self.draft_payload = draft_payload
        self.dry_run = dry_run

        # 生成ID
        self.task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.sample_id = sample_id or f"sample_{uuid.uuid4().hex[:8]}"

        # 初始化守卫和工具
        self.account_scope_guard = AccountScopeGuard()
        self.page_state_classifier = PageStateClassifier()
        self.pre_publish_guard = PrePublishGuard()
        self.human_confirmation_guard = HumanConfirmationGuard(simulation_mode=True)
        self.publish_result_verifier = PublishResultVerifier()

        # 审计日志器
        self.audit_logger = get_default_audit_logger()

        # 流程状态
        self.current_step = 0
        self.steps_log = []
        self.audit_events_log = []

        # 中间结果
        self.platform_config = None
        self.authorized_account_config = None
        self.draft_template = None
        self.account_scope_check_result = None
        self.page_state_classification_result = None
        self.draft_validation_result = None
        self.pre_publish_guard_result = None
        self.human_confirmation_result = None
        self.publish_verification_result = None

        # Mock数据（Phase 1 专用）
        self.mock_app_package = "com.example.app"  # 模拟App包名
        self.mock_vision_text = "标题 正文 发布前确认"  # 模拟视觉文本
        self.mock_ui_anchors = ["标题", "正文", "发布"]  # 模拟UI锚点
        self.mock_publish_result_page_state = (
            Phase1PageState.PUBLISH_SUCCESS.value
        )  # 模拟发布结果页面状态

    def _log_step(self, step_name: str, status: str, details: dict | None = None) -> None:
        """记录步骤执行日志"""
        step_info = {
            "step": self.current_step,
            "name": step_name,
            "status": status,
            "details": details or {},
        }
        self.steps_log.append(step_info)
        self.current_step += 1

        # 输出日志（简化版）
        print(f"[步骤{step_info['step']}] {step_name}: {status}")
        if details:
            for key, value in details.items():
                if isinstance(value, dict):
                    print(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    print(f"  {key}: {value}")

    def _log_audit_event(
        self,
        action: str,
        allowed: bool,
        reason: str,
        page_state: str = "",
        evidence: list[str] = None,
    ) -> None:
        """记录审计事件"""
        audit_event = AuditEvent(
            task_id=self.task_id,
            sample_id=self.sample_id,
            account_id=(
                self.authorized_account_config.get("account_id", "")
                if self.authorized_account_config
                else ""
            ),
            platform_id=self.platform_config.get("platform_id", "") if self.platform_config else "",
            page_state=page_state,
            action=action,  # 审计动作字符串
            allowed=allowed,
            reason=reason,
            evidence=evidence or [],
            metadata={"dry_run": self.dry_run, "task_id": self.task_id},
        )

        try:
            log_audit_event(audit_event)
            self.audit_events_log.append(action)
            print(f"[审计] {action}: {reason}")
        except Exception as e:
            print(f"[审计错误] 记录事件失败: {e}")
            raise RuntimeError(f"审计事件记录失败: {e}")

    def _load_configs(self) -> None:
        """加载配置文件"""
        # 步骤1: 读取平台配置
        try:
            with open(self.platform_config_path, encoding="utf-8") as f:
                self.platform_config = yaml.safe_load(f)
            self._log_step("读取平台配置", "成功", {"path": self.platform_config_path})
        except Exception as e:
            self._log_step("读取平台配置", "失败", {"error": str(e)})
            raise RuntimeError(f"加载平台配置失败: {e}")

        # 步骤2: 读取授权账号配置
        try:
            with open(self.authorized_account_config_path, encoding="utf-8") as f:
                self.authorized_account_config = yaml.safe_load(f)
            self._log_step(
                "读取授权账号配置", "成功", {"path": self.authorized_account_config_path}
            )
        except Exception as e:
            self._log_step("读取授权账号配置", "失败", {"error": str(e)})
            raise RuntimeError(f"加载授权账号配置失败: {e}")

    def _validate_draft_payload(self) -> bool:
        """校验草稿payload（复用已有逻辑）"""
        try:
            # 加载草稿模板
            with open(self.draft_template_path, encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

            # 创建模板对象
            self.draft_template = DraftFormTemplate(template_data)

            # 将payload字典转换为DraftFormPayload对象
            from athena.open_human.phase1.templates.form_template_schema import (
                DraftFormPayload,
            )

            payload_obj = DraftFormPayload.from_dict(self.draft_payload)

            # 使用模板对象的validate_payload方法校验
            validation_result = self.draft_template.validate_payload(payload_obj)
            self.draft_validation_result = validation_result

            details = {
                "valid": validation_result.valid,
                "missing_fields": validation_result.missing_fields,
                "violations": validation_result.violations,
            }

            if validation_result.valid:
                self._log_step("校验草稿payload", "成功", details)
                return True
            else:
                self._log_step("校验草稿payload", "失败", details)
                return False

        except Exception as e:
            self._log_step("校验草稿payload", "异常", {"error": str(e)})
            raise RuntimeError(f"草稿校验失败: {e}")

    def _get_draft_validation_evidence(self) -> list[str]:
        """获取草稿校验的证据列表"""
        evidence = []
        if self.draft_validation_result:
            if not self.draft_validation_result.valid:
                evidence.append("草稿校验失败")
                if self.draft_validation_result.missing_fields:
                    evidence.append(
                        f"缺失字段: {', '.join(self.draft_validation_result.missing_fields)}"
                    )
                if self.draft_validation_result.violations:
                    for violation in self.draft_validation_result.violations[:5]:  # 限制数量
                        evidence.append(f"违规: {violation}")
            else:
                evidence.append("草稿校验通过")
        else:
            evidence.append("无校验结果")
        return evidence

    def _launch_target_app(self) -> bool:
        """
        启动目标 App（Phase 2 替换点）

        根据 dry_run 模式使用真实启动能力或 mock。

        Returns:
            bool: 启动是否成功
        """
        try:
            if self.dry_run:
                # dry_run 模式使用 mock 启动
                self._log_step(
                    "启动目标App (dry_run模式)",
                    "模拟执行",
                    {"app_package": self.mock_app_package, "note": "dry_run模式使用mock启动"},
                )
                launch_success = True
            else:
                # 非 dry_run 模式，使用真实启动能力
                if PHASE2_APP_LAUNCHER_AVAILABLE:
                    self._log_step(
                        "启动目标App (真实模式)",
                        "执行中",
                        {"app_package": self.mock_app_package, "note": "使用Phase 2 App启动器"},
                    )

                    # 使用真实启动器
                    result = launch_app_real(
                        app_package=self.mock_app_package,
                        dry_run=False,
                        device_id=None,  # 使用默认设备
                    )

                    launch_success = result.success

                    # 记录详细结果
                    self._log_step(
                        "App启动结果",
                        "成功" if result.success else "失败",
                        {
                            "success": result.success,
                            "current_package": result.current_package,
                            "reason": result.reason,
                            "result_code": (
                                result.result_code.value
                                if hasattr(result.result_code, "value")
                                else str(result.result_code)
                            ),
                            "evidence_count": len(result.evidence),
                        },
                    )
                else:
                    # Phase 2 模块不可用，回退到 mock
                    self._log_step(
                        "启动目标App (回退mock)",
                        "模拟执行",
                        {
                            "app_package": self.mock_app_package,
                            "note": "Phase 2模块不可用，使用回退mock",
                            "warning": "需要安装Phase 2模块以获得真实启动能力",
                        },
                    )
                    launch_success = True

            # 更新 mock 包名（用于后续步骤）
            if launch_success:
                self.mock_app_package = self.mock_app_package  # 保持不变，或可根据实际情况更新

            return launch_success

        except Exception as e:
            self._log_step(
                "启动目标App", "异常", {"error": str(e), "app_package": self.mock_app_package}
            )
            return False

    def _mock_app_navigation(self, target: str) -> None:
        """
        Mock App 导航（Phase 1 专用）

        Args:
            target: 导航目标 ("launch", "create_entry", "draft_edit", "pre_publish_review", "publish_action")
        """
        mock_map = {
            "launch": "启动App",
            "create_entry": "导航到创建入口",
            "draft_edit": "进入草稿编辑页",
            "pre_publish_review": "到达发布前确认页",
            "publish_action": "执行发布动作",
        }

        if target in mock_map:
            self._log_step(
                f"Mock: {mock_map[target]}",
                "模拟执行",
                {"note": "Phase 1 中使用 mock/stub，保留清晰接口位", "target": target},
            )
        else:
            self._log_step(f"Mock导航: {target}", "未知目标", {"warning": "未知导航目标"})

    def _navigate_to_create_entry(self) -> bool:
        """
        导航到创建入口（Phase 2 替换点）

        根据 dry_run 模式使用真实导航能力或 mock。

        Returns:
            bool: 导航是否成功
        """
        try:
            # 记录开始事件
            self._log_audit_event(
                action="navigate_to_create_entry_started",
                allowed=True,
                reason="开始导航到创建入口",
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"App包名: {self.mock_app_package}", f"dry_run: {self.dry_run}"],
            )

            if self.dry_run:
                # dry_run 模式使用 mock 导航
                self._log_step(
                    "导航到创建入口 (dry_run模式)",
                    "模拟执行",
                    {"app_package": self.mock_app_package, "note": "dry_run模式使用mock导航"},
                )

                # 使用 CreateEntryNavigator 的 dry_run 模式
                if PHASE2_CREATE_ENTRY_NAVIGATOR_AVAILABLE:
                    result = navigate_to_create_entry(
                        app_package=self.mock_app_package,
                        current_package=self.mock_app_package,
                        vision_text=self.mock_vision_text,
                        ui_anchors=self.mock_ui_anchors,
                        dry_run=True,
                        device_id=None,  # 使用默认设备
                    )

                    navigation_success = result.success
                    navigation_reason = result.reason

                    # 记录详细结果
                    self._log_step(
                        "创建入口导航结果",
                        "成功" if result.success else "失败",
                        {
                            "success": result.success,
                            "final_page_state": result.final_page_state,
                            "reason": result.reason,
                            "result_code": (
                                result.result_code.value
                                if hasattr(result.result_code, "value")
                                else str(result.result_code)
                            ),
                            "evidence_count": len(result.evidence),
                        },
                    )
                else:
                    # Phase 2 模块不可用，回退到 mock
                    navigation_success = True
                    navigation_reason = "Phase 2 模块不可用，使用 mock 导航"
                    self._log_step(
                        "创建入口导航 (mock)",
                        "模拟成功",
                        {"note": "Phase 2 模块不可用，使用 mock 导航"},
                    )
            else:
                # 真实模式使用真实导航能力
                self._log_step(
                    "导航到创建入口 (真实模式)",
                    "开始执行",
                    {"app_package": self.mock_app_package, "note": "真实模式使用 Phase 2 导航器"},
                )

                if PHASE2_CREATE_ENTRY_NAVIGATOR_AVAILABLE:
                    result = navigate_to_create_entry(
                        app_package=self.mock_app_package,
                        current_package=self.mock_app_package,
                        vision_text=self.mock_vision_text,
                        ui_anchors=self.mock_ui_anchors,
                        dry_run=False,
                        device_id=None,  # 使用默认设备
                    )

                    navigation_success = result.success
                    navigation_reason = result.reason

                    # 记录详细结果
                    self._log_step(
                        "创建入口导航结果",
                        "成功" if result.success else "失败",
                        {
                            "success": result.success,
                            "final_page_state": result.final_page_state,
                            "reason": result.reason,
                            "result_code": (
                                result.result_code.value
                                if hasattr(result.result_code, "value")
                                else str(result.result_code)
                            ),
                            "evidence_count": len(result.evidence),
                        },
                    )
                else:
                    # Phase 2 模块不可用，无法执行真实导航
                    navigation_success = False
                    navigation_reason = "Phase 2 模块不可用，无法执行真实导航"
                    self._log_step(
                        "创建入口导航", "失败", {"error": "Phase 2 模块不可用，无法执行真实导航"}
                    )

            # 记录结束事件
            self._log_audit_event(
                action="navigate_to_create_entry_completed",
                allowed=navigation_success,
                reason=navigation_reason,
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"导航结果: {navigation_success}", f"原因: {navigation_reason}"],
            )

            return navigation_success

        except Exception as e:
            # 异常处理
            self._log_step(
                "导航到创建入口", "异常", {"error": str(e), "app_package": self.mock_app_package}
            )

            self._log_audit_event(
                action="navigate_to_create_entry_failed",
                allowed=False,
                reason=f"导航异常: {str(e)}",
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"异常: {str(e)}"],
            )

            return False

    def _navigate_to_draft_edit(self) -> bool:
        """
        导航到草稿编辑页（Phase 2 替换点）

        根据 dry_run 模式使用真实导航能力或 mock。

        Returns:
            bool: 导航是否成功
        """
        try:
            # 记录开始事件
            self._log_audit_event(
                action="navigate_to_draft_edit_started",
                allowed=True,
                reason="开始导航到草稿编辑页",
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"App包名: {self.mock_app_package}", f"dry_run: {self.dry_run}"],
            )

            if self.dry_run:
                # dry_run 模式使用 mock 导航
                self._log_step(
                    "导航到草稿编辑页 (dry_run模式)",
                    "模拟执行",
                    {"app_package": self.mock_app_package, "note": "dry_run模式使用mock导航"},
                )

                # 使用 DraftEditNavigator 的 dry_run 模式
                if PHASE2_DRAFT_EDIT_NAVIGATOR_AVAILABLE:
                    result = navigate_to_draft_edit(
                        app_package=self.mock_app_package,
                        current_package=self.mock_app_package,
                        vision_text=self.mock_vision_text,
                        ui_anchors=self.mock_ui_anchors,
                        dry_run=True,
                        device_id=None,  # 使用默认设备
                    )

                    navigation_success = result.success
                    navigation_reason = result.reason

                    # 记录详细结果
                    self._log_step(
                        "草稿编辑页导航结果",
                        "成功" if result.success else "失败",
                        {
                            "success": result.success,
                            "final_page_state": result.final_page_state,
                            "reason": result.reason,
                            "result_code": (
                                result.result_code.value
                                if hasattr(result.result_code, "value")
                                else str(result.result_code)
                            ),
                            "evidence_count": len(result.evidence),
                        },
                    )
                else:
                    # Phase 2 模块不可用，回退到 mock
                    navigation_success = True
                    navigation_reason = "Phase 2 模块不可用，使用 mock 导航"
                    self._log_step(
                        "草稿编辑页导航 (mock)",
                        "模拟成功",
                        {"note": "Phase 2 模块不可用，使用 mock 导航"},
                    )
            else:
                # 真实模式使用真实导航能力
                self._log_step(
                    "导航到草稿编辑页 (真实模式)",
                    "开始执行",
                    {"app_package": self.mock_app_package, "note": "真实模式使用 Phase 2 导航器"},
                )

                if PHASE2_DRAFT_EDIT_NAVIGATOR_AVAILABLE:
                    result = navigate_to_draft_edit(
                        app_package=self.mock_app_package,
                        current_package=self.mock_app_package,
                        vision_text=self.mock_vision_text,
                        ui_anchors=self.mock_ui_anchors,
                        dry_run=False,
                        device_id=None,  # 使用默认设备
                    )

                    navigation_success = result.success
                    navigation_reason = result.reason

                    # 记录详细结果
                    self._log_step(
                        "草稿编辑页导航结果",
                        "成功" if result.success else "失败",
                        {
                            "success": result.success,
                            "final_page_state": result.final_page_state,
                            "reason": result.reason,
                            "result_code": (
                                result.result_code.value
                                if hasattr(result.result_code, "value")
                                else str(result.result_code)
                            ),
                            "evidence_count": len(result.evidence),
                        },
                    )
                else:
                    # Phase 2 模块不可用，无法执行真实导航
                    navigation_success = False
                    navigation_reason = "Phase 2 模块不可用，无法执行真实导航"
                    self._log_step(
                        "草稿编辑页导航", "失败", {"error": "Phase 2 模块不可用，无法执行真实导航"}
                    )

            # 记录结束事件
            self._log_audit_event(
                action="navigate_to_draft_edit_completed",
                allowed=navigation_success,
                reason=navigation_reason,
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"导航结果: {navigation_success}", f"原因: {navigation_reason}"],
            )

            return navigation_success

        except Exception as e:
            # 异常处理
            self._log_step(
                "导航到草稿编辑页", "异常", {"error": str(e), "app_package": self.mock_app_package}
            )

            self._log_audit_event(
                action="navigate_to_draft_edit_failed",
                allowed=False,
                reason=f"导航异常: {str(e)}",
                page_state=(
                    self.page_state_classification_result.page_state
                    if self.page_state_classification_result
                    else ""
                ),
                evidence=[f"异常: {str(e)}"],
            )

            return False

    def run(self) -> CompliantMVPFlowResult:
        """
        执行合规 MVP 主流程

        严格按26个步骤顺序执行，返回标准化结果。
        """
        print("=== Phase 1 合规 MVP 流程开始 ===")
        print(f"任务ID: {self.task_id}, 样本ID: {self.sample_id}")
        print(f"Dry-run 模式: {self.dry_run}")

        try:
            # === 步骤1-2: 加载配置 ===
            self._load_configs()

            # === 步骤3: 执行账号边界检查 ===
            requested_account_id = self.authorized_account_config.get("account_id", "")
            requested_platform_id = self.platform_config.get("platform_id", "")

            self.account_scope_check_result = check_account_scope(
                requested_account_id, requested_platform_id, self.authorized_account_config
            )

            step3_details = {
                "allowed": self.account_scope_check_result.allowed,
                "reason": self.account_scope_check_result.reason,
            }
            self._log_step(
                "执行账号边界检查",
                "成功" if self.account_scope_check_result.allowed else "失败",
                step3_details,
            )

            # === 步骤4: 记录审计事件：account_scope_check ===
            self._log_audit_event(
                action="account_scope_check",
                allowed=self.account_scope_check_result.allowed,
                reason=self.account_scope_check_result.reason,
                page_state="",
                evidence=[f"账号ID: {requested_account_id}", f"平台ID: {requested_platform_id}"],
            )

            # 检查账号范围结果，失败则结束
            if not self.account_scope_check_result.allowed:
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="safe_stop",  # 按语义，账号范围失败应安全停止
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="account_scope_violation",
                    sub_reason="account_id_mismatch_or_not_allowed",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # === 步骤5: 进入目标 App（Phase 1 中可用 mock / stub）===
            self._mock_app_navigation("launch")

            # === 步骤6: 记录审计事件：launch_app ===
            self._log_audit_event(
                action="launch_app",
                allowed=True,
                reason=f"模拟启动App: {self.mock_app_package}",
                page_state="LAUNCH_SCREEN",
                evidence=[f"App包名: {self.mock_app_package}", "使用mock数据"],
            )

            # === 步骤7: 分类当前页面状态 ===
            self.page_state_classification_result = self.page_state_classifier.classify(
                app_package=self.mock_app_package,
                current_package=self.mock_app_package,
                vision_text=self.mock_vision_text,
                ui_anchors=self.mock_ui_anchors,
            )

            step7_details = {
                "page_state": self.page_state_classification_result.page_state,
                "confidence": self.page_state_classification_result.confidence,
                "evidence": self.page_state_classification_result.evidence[:3],  # 只显示前3条
            }
            self._log_step("分类当前页面状态", "成功", step7_details)

            # === 步骤8: 记录审计事件：page_state_classified ===
            self._log_audit_event(
                action="page_state_classified",
                allowed=True,
                reason=f"页面状态分类为: {self.page_state_classification_result.page_state}",
                page_state=self.page_state_classification_result.page_state,
                evidence=self.page_state_classification_result.evidence[:5],
            )

            # === 步骤9: 进入或模拟进入创建入口 ===
            self._mock_app_navigation("create_entry")

            # === 步骤10: 进入或模拟进入草稿编辑页 ===
            draft_edit_success = self._navigate_to_draft_edit()
            if not draft_edit_success:
                self._log_audit_event(
                    action="navigate_to_draft_edit_failed",
                    allowed=False,
                    reason="草稿编辑页导航失败",
                    page_state=(
                        self.page_state_classification_result.page_state
                        if self.page_state_classification_result
                        else ""
                    ),
                    evidence=[f"App包名: {self.mock_app_package}", "导航到草稿编辑页失败"],
                )
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="fail",
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="draft_edit_navigation_failed",
                    sub_reason="navigation_to_draft_edit_failed",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # === 步骤11: 加载草稿模板 ===
            self._log_step("加载草稿模板", "成功", {"path": self.draft_template_path})

            # === 步骤12: 校验草稿 payload ===
            draft_valid = self._validate_draft_payload()

            # === 步骤13: 记录审计事件：draft_validated ===
            self._log_audit_event(
                action="draft_validated",
                allowed=draft_valid,
                reason="草稿校验通过" if draft_valid else "草稿校验失败",
                page_state=self.page_state_classification_result.page_state,
                evidence=self._get_draft_validation_evidence(),
            )

            # 检查草稿校验结果
            if not draft_valid:
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="fail",  # 草稿校验失败视为失败
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="draft_validation_failed",
                    sub_reason="invalid_draft_payload",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # === 步骤14: 到达或模拟到达发布前确认页 ===
            self._mock_app_navigation("pre_publish_review")

            # === 步骤15: 执行 pre_publish_guard.check(...) ===
            self.pre_publish_guard_result = check_pre_publish_conditions(
                account_scope_ok=self.account_scope_check_result.allowed,
                page_state=self.page_state_classification_result.page_state,
                draft_valid=draft_valid,
            )

            step15_details = {
                "allowed": self.pre_publish_guard_result.allowed,
                "reason": self.pre_publish_guard_result.reason,
                "requires_human_confirmation": self.pre_publish_guard_result.requires_human_confirmation,
            }
            self._log_step(
                "执行pre_publish_guard检查",
                "通过" if self.pre_publish_guard_result.allowed else "失败",
                step15_details,
            )

            # === 步骤16: 记录审计事件：pre_publish_guard_checked ===
            self._log_audit_event(
                action="pre_publish_guard_checked",
                allowed=self.pre_publish_guard_result.allowed,
                reason=self.pre_publish_guard_result.reason,
                page_state=self.page_state_classification_result.page_state,
                evidence=[
                    f"需要人工确认: {self.pre_publish_guard_result.requires_human_confirmation}"
                ],
            )

            # === 步骤17: 若不允许放行，则立即结束并返回 fail 或 safe_stop（按语义判断）===
            if not self.pre_publish_guard_result.allowed:
                # 根据pre_publish_guard的结果判断状态
                final_status = "fail"  # 默认为失败
                taxonomy_class = "pre_publish_check_failed"
                sub_reason = "guard_not_allowed"

                # 如果是因为页面状态问题，可能是safe_stop
                if "页面状态不是发布前确认状态" in self.pre_publish_guard_result.reason:
                    final_status = "safe_stop"
                    taxonomy_class = "unsafe_to_continue"
                    sub_reason = "wrong_page_state_for_publish"

                return CompliantMVPFlowResult(
                    success=False,
                    final_status=final_status,
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class=taxonomy_class,
                    sub_reason=sub_reason,
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # === 步骤18: 请求人工确认 ===
            draft_summary = {
                "title": self.draft_payload.get("title", "无标题"),
                "body_preview": (
                    str(self.draft_payload.get("body", ""))[:100] + "..."
                    if self.draft_payload.get("body")
                    else "空内容"
                ),
                "tags": self.draft_payload.get("tags", []),
                "task_id": self.task_id,
            }

            self.human_confirmation_result = self.human_confirmation_guard.request_confirmation(
                task_id=self.task_id,
                account_id=requested_account_id,
                page_state=self.page_state_classification_result.page_state,
                draft_summary=draft_summary,
            )

            step18_details = {
                "decision": self.human_confirmation_result.decision,
                "confirmed": self.human_confirmation_result.confirmed,
                "reason": self.human_confirmation_result.reason,
            }
            self._log_step("请求人工确认", "完成", step18_details)

            # === 步骤19: 记录审计事件：human_confirmation_received ===
            self._log_audit_event(
                action="human_confirmation_received",
                allowed=self.human_confirmation_result.confirmed,
                reason=f"人工确认结果: {self.human_confirmation_result.decision}",
                page_state=self.page_state_classification_result.page_state,
                evidence=[
                    f"决策: {self.human_confirmation_result.decision}",
                    f"操作员: {self.human_confirmation_result.operator_id or '无'}",
                ],
            )

            # === 步骤20-22: 处理人工确认结果 ===
            if self.human_confirmation_result.decision == ConfirmationDecision.CANCEL.value:
                # 步骤20: decision=cancel -> final_status=cancelled
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="cancelled",
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="human_cancelled",
                    sub_reason="operator_cancelled_task",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            elif self.human_confirmation_result.decision == ConfirmationDecision.TIMEOUT.value:
                # 步骤21: decision=timeout -> final_status=safe_stop, taxonomy_class="unsafe_to_continue"
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="safe_stop",
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="unsafe_to_continue",
                    sub_reason="human_confirmation_timeout",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # 步骤22: 只有 decision=continue 才允许进入"发布动作接口位"
            elif self.human_confirmation_result.decision == ConfirmationDecision.CONTINUE.value:
                # 继续流程
                pass
            else:
                # 未知决策，安全停止
                return CompliantMVPFlowResult(
                    success=False,
                    final_status="safe_stop",
                    task_id=self.task_id,
                    sample_id=self.sample_id,
                    taxonomy_class="unsafe_to_continue",
                    sub_reason="unknown_human_decision",
                    flow_steps=self.steps_log,
                    audit_events=self.audit_events_log,
                )

            # === 步骤23: 记录审计事件：publish_action ===
            self._log_audit_event(
                action="publish_action",
                allowed=True,
                reason="进入发布动作接口位（Phase 1 mock）",
                page_state=self.page_state_classification_result.page_state,
                evidence=["使用mock发布动作", "Phase 1 不执行真实发布"],
            )

            # === 步骤24: 调用发布结果核验器 verify(...) ===
            self.publish_verification_result = verify_publish_result(
                page_state=self.mock_publish_result_page_state,
                vision_text=self.mock_vision_text,
                ui_anchors=self.mock_ui_anchors,
            )

            step24_details = {
                "result": self.publish_verification_result.result,
                "page_state": self.publish_verification_result.page_state,
                "taxonomy_class": self.publish_verification_result.taxonomy_class,
                "sub_reason": self.publish_verification_result.sub_reason,
            }
            self._log_step("调用发布结果核验器", "完成", step24_details)

            # === 步骤25: 记录审计事件：publish_result_verified ===
            self._log_audit_event(
                action="publish_result_verified",
                allowed=self.publish_verification_result.result == "success",
                reason=f"发布结果核验: {self.publish_verification_result.result}",
                page_state=self.publish_verification_result.page_state,
                evidence=self.publish_verification_result.evidence[:3],
            )

            # === 步骤26: 生成并返回 CompliantMVPFlowResult ===
            # 根据核验结果确定最终状态
            verifier_result = self.publish_verification_result.result
            if verifier_result == "success":
                final_status = "success"
                success = True
            elif verifier_result == "fail":
                final_status = "fail"
                success = False
            elif verifier_result == "safe_stop":
                final_status = "safe_stop"
                success = False
            else:
                # 未知结果，保守处理
                final_status = "safe_stop"
                success = False

            result = CompliantMVPFlowResult(
                success=success,
                final_status=final_status,
                task_id=self.task_id,
                sample_id=self.sample_id,
                taxonomy_class=self.publish_verification_result.taxonomy_class,
                sub_reason=self.publish_verification_result.sub_reason,
                flow_steps=self.steps_log,
                audit_events=self.audit_events_log,
            )

            print("=== Phase 1 合规 MVP 流程结束 ===")
            print(f"最终状态: {final_status}, 成功: {success}")

            return result

        except Exception as e:
            # 异常处理
            error_step = f"步骤{self.current_step}" if self.current_step > 0 else "未知步骤"
            self._log_step("流程异常", "失败", {"error": str(e), "step": error_step})

            return CompliantMVPFlowResult(
                success=False,
                final_status="fail",  # 异常视为失败
                task_id=self.task_id,
                sample_id=self.sample_id,
                taxonomy_class="flow_execution_error",
                sub_reason=str(e)[:100],  # 截断过长的错误信息
                flow_steps=self.steps_log,
                audit_events=self.audit_events_log,
            )


# ========== dry-run 入口 ==========


def create_mock_draft_payload() -> dict[str, Any]:
    """创建模拟草稿payload"""
    return {
        "title": "测试标题 - Phase 1 合规MVP流程",
        "body": "这是测试正文内容，用于验证 Phase 1 合规MVP流程的执行。\n包含多行文本和必要的字段。",
        "tags": ["测试", "Phase1", "合规MVP"],
        "category": "技术",
        "visibility": "公开",
    }


def main():
    """主函数：dry-run 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 合规 MVP 流程 dry-run 入口")
    parser.add_argument(
        "--platform-config",
        type=str,
        default="athena/open_human/phase1/configs/platform_profile.yaml",
        help="平台配置文件路径",
    )
    parser.add_argument(
        "--account-config",
        type=str,
        default="athena/open_human/phase1/configs/authorized_account.yaml",
        help="授权账号配置文件路径",
    )
    parser.add_argument(
        "--draft-template",
        type=str,
        default="athena/open_human/phase1/templates/draft_form_template.yaml",
        help="草稿模板文件路径",
    )
    parser.add_argument(
        "--human-decision",
        type=str,
        choices=["continue", "cancel", "timeout"],
        default="continue",
        help="模拟人工确认决策",
    )
    parser.add_argument(
        "--publish-result-state",
        type=str,
        default="PUBLISH_SUCCESS",
        choices=["PUBLISH_SUCCESS", "PUBLISH_FAILURE", "RISK_PROMPT", "UNKNOWN"],
        help="模拟发布结果页面状态",
    )
    parser.add_argument("--output-json", action="store_true", help="输出JSON格式结果")

    args = parser.parse_args()

    print("=== Phase 1 合规 MVP 流程 dry-run ===")

    # 创建流程实例
    flow = CompliantMVPFlow(
        platform_config_path=args.platform_config,
        authorized_account_config_path=args.account_config,
        draft_template_path=args.draft_template,
        draft_payload=create_mock_draft_payload(),
        dry_run=True,
        task_id=f"dryrun_{uuid.uuid4().hex[:8]}",
        sample_id=f"dryrun_sample_{uuid.uuid4().hex[:8]}",
    )

    # 设置模拟参数 - 将大写参数转换为 Phase1PageState 枚举值
    from athena.open_human.phase1.states.page_state_schema import Phase1PageState

    flow.mock_publish_result_page_state = Phase1PageState.from_string(
        args.publish_result_state
    ).value

    # 根据人工确认决策设置模拟结果
    if args.human_decision == "cancel":
        flow.human_confirmation_guard = HumanConfirmationGuard(simulation_mode=True)
        flow.human_confirmation_result = flow.human_confirmation_guard.simulate_cancel(
            flow.task_id,
            (
                flow.authorized_account_config.get("account_id", "")
                if flow.authorized_account_config
                else ""
            ),
            (
                flow.page_state_classification_result.page_state
                if flow.page_state_classification_result
                else ""
            ),
            {},
        )
    elif args.human_decision == "timeout":
        flow.human_confirmation_guard = HumanConfirmationGuard(simulation_mode=True)
        flow.human_confirmation_result = flow.human_confirmation_guard.simulate_timeout(
            flow.task_id,
            (
                flow.authorized_account_config.get("account_id", "")
                if flow.authorized_account_config
                else ""
            ),
            (
                flow.page_state_classification_result.page_state
                if flow.page_state_classification_result
                else ""
            ),
            {},
        )
    # continue 使用默认模拟

    # 执行流程
    result = flow.run()

    # 输出结果
    print("\n=== 流程结果摘要 ===")
    print(f"成功: {result.success}")
    print(f"最终状态: {result.final_status}")
    print(f"任务ID: {result.task_id}")
    print(f"样本ID: {result.sample_id}")
    if result.taxonomy_class:
        print(f"分类标识: {result.taxonomy_class}")
    if result.sub_reason:
        print(f"子原因: {result.sub_reason}")

    print(f"\n执行步骤数: {len(result.flow_steps)}")
    print(f"审计事件数: {len(result.audit_events)}")

    # 输出JSON格式（如果指定）
    if args.output_json:
        print("\n=== JSON 格式结果 ===")
        print(result.to_json())

    # 返回退出码
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
