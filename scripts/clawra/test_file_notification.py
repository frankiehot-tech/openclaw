#!/usr/bin/env python3
"""测试文件通知功能"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from maref_notifier import MAREFNotifier

notifier = MAREFNotifier("config/notifier_config.json")

print(f"配置文件路径: {notifier.config.get('file_log_path')}")

# 检查文件路径
log_path = Path(notifier.config.get("file_log_path", "/var/log/maref_notifications.log"))
print(f"日志文件路径: {log_path}")
print(f"日志文件是否存在: {log_path.exists()}")
print(f"日志文件父目录是否存在: {log_path.parent.exists()}")
print(f"日志文件父目录可写: {os.access(log_path.parent, os.W_OK)}")

# 测试文件通知
test_message = "测试文件通知消息"
success = notifier.send_file_notification("测试标题", test_message)
print(f"文件通知发送结果: {success}")

if not success:
    print("尝试手动创建文件...")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
        print(f"文件创建成功: {log_path.exists()}")

        # 再次测试
        success = notifier.send_file_notification("测试标题", test_message)
        print(f"第二次文件通知发送结果: {success}")
    except Exception as e:
        print(f"手动创建文件失败: {e}")
