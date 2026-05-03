"""
Audit Logger for Phase 1 - Phase 1 审计日志器

实现审计事件的日志记录，支持 JSON Lines 格式输出。
优先复用现有日志风格，但审计事件需要结构化存储。
"""

import json
import logging
import os
from datetime import datetime

from .audit_schema import AuditEvent


class AuditLogger:
    """
    Phase 1 审计日志器

    将审计事件记录到文件，支持 JSON Lines 格式。
    每条事件一行 JSON，便于后续分析处理。
    """

    def __init__(
        self,
        output_dir: str | None = None,
        filename_prefix: str = "audit",
        use_json_lines: bool = True,
    ):
        """
        初始化审计日志器

        Args:
            output_dir: 日志输出目录，默认为 artifacts/open_human_phase1/audit/
            filename_prefix: 日志文件名前缀
            use_json_lines: 是否使用 JSON Lines 格式（True 优先）
        """
        # 设置默认输出目录
        if output_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            output_dir = os.path.join(project_root, "artifacts", "open_human_phase1", "audit")

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 生成日志文件名（包含日期）
        date_str = datetime.now().strftime("%Y%m%d")
        log_filename = f"{filename_prefix}_{date_str}.log"
        self.log_path = os.path.join(output_dir, log_filename)

        self.use_json_lines = use_json_lines

        # 配置日志（复用现有日志风格）
        self.logger = logging.getLogger(f"athena.audit.{filename_prefix}")
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(self.log_path, encoding="utf-8")

            if use_json_lines:
                # JSON Lines 格式：每条日志事件本身是 JSON，不需要额外格式化
                file_handler.setFormatter(logging.Formatter("%(message)s"))
            else:
                # 文本格式（复用现有风格）
                file_handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )

            self.logger.addHandler(file_handler)

        # 记录初始化信息（非审计事件）
        self.logger.info(f"AuditLogger 初始化，日志路径: {self.log_path}")
        if use_json_lines:
            self.logger.info("使用 JSON Lines 格式")
        else:
            self.logger.info("使用文本格式")

    def append_event(self, event: AuditEvent) -> None:
        """
        添加审计事件到日志

        Args:
            event: 审计事件对象

        Raises:
            IOError: 当写入日志文件失败时
            ValueError: 当事件数据无效时
        """
        try:
            # 将事件转换为字典
            event_dict = event.to_dict()

            if self.use_json_lines:
                # JSON Lines 格式：直接输出 JSON 字符串
                json_str = json.dumps(event_dict, ensure_ascii=False)
                self.logger.info(json_str)
            else:
                # 文本格式：将事件字典作为字符串记录
                # 这里为了兼容现有日志格式，将事件信息格式化为字符串
                event_summary = (
                    f"action={event.action}, "
                    f"page_state={event.page_state}, "
                    f"allowed={event.allowed}, "
                    f"reason={event.reason}"
                )
                self.logger.info(f"审计事件: {event_summary}")

                # 如果需要详细数据，也可以单独记录
                if event.evidence:
                    evidence_str = ", ".join(event.evidence[:3])  # 只显示前3条证据
                    if len(event.evidence) > 3:
                        evidence_str += f" ...(+{len(event.evidence)-3})"
                    self.logger.debug(f"证据: {evidence_str}")

            # 立即刷新，确保数据写入（重要事件不丢失）
            for handler in self.logger.handlers:
                handler.flush()

        except (json.JSONDecodeError, TypeError) as e:
            # 事件数据序列化失败
            error_msg = f"审计事件序列化失败: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
        except OSError as e:
            # 文件写入失败
            error_msg = f"写入审计日志失败: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e
        except Exception as e:
            # 其他异常
            error_msg = f"记录审计事件异常: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_log_path(self) -> str:
        """获取当前日志文件路径"""
        return self.log_path

    def get_output_dir(self) -> str:
        """获取输出目录"""
        return os.path.dirname(self.log_path)

    def close(self) -> None:
        """关闭日志处理器"""
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)


# 全局默认审计日志器实例
_default_audit_logger: AuditLogger | None = None


def get_default_audit_logger() -> AuditLogger:
    """
    获取全局默认审计日志器（单例模式）

    Returns:
        AuditLogger: 默认审计日志器实例
    """
    global _default_audit_logger

    if _default_audit_logger is None:
        # 使用默认配置：JSON Lines 格式，默认输出目录
        _default_audit_logger = AuditLogger(
            output_dir=None, filename_prefix="phase1_audit", use_json_lines=True  # 使用默认目录
        )

    return _default_audit_logger


def log_audit_event(event: AuditEvent) -> None:
    """
    记录审计事件的便捷函数

    Args:
        event: 审计事件对象
    """
    logger = get_default_audit_logger()
    logger.append_event(event)


# 工厂函数：创建特定用途的审计日志器
def create_account_scope_audit_logger() -> AuditLogger:
    """创建账号范围检查专用的审计日志器"""
    return AuditLogger(output_dir=None, filename_prefix="account_scope_audit", use_json_lines=True)


def create_page_state_audit_logger() -> AuditLogger:
    """创建页面状态分类专用的审计日志器"""
    return AuditLogger(output_dir=None, filename_prefix="page_state_audit", use_json_lines=True)


def create_publish_result_audit_logger() -> AuditLogger:
    """创建发布结果核验专用的审计日志器"""
    return AuditLogger(output_dir=None, filename_prefix="publish_result_audit", use_json_lines=True)


# 示例使用
if __name__ == "__main__":
    # 示例：创建并记录一个审计事件
    try:
        # 使用默认日志器
        logger = get_default_audit_logger()
        print(f"审计日志路径: {logger.get_log_path()}")

        # 创建一个示例事件
        from .audit_schema import AuditAction, AuditEvent

        example_event = AuditEvent(
            task_id="task_123",
            sample_id="sample_456",
            account_id="account_789",
            platform_id="weibo",
            page_state="publish_success",
            action=AuditAction.PUBLISH_RESULT_VERIFIED,
            allowed=True,
            reason="发布成功验证通过",
            evidence=["页面显示'发布成功'", "无错误提示"],
            metadata={"test": "example"},
        )

        # 记录事件
        logger.append_event(example_event)
        print("示例审计事件已记录")

        # 使用便捷函数
        log_audit_event(example_event)
        print("便捷函数记录成功")

    except Exception as e:
        print(f"示例执行失败: {e}")
        import traceback

        traceback.print_exc()
