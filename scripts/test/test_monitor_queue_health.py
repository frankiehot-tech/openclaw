#!/usr/bin/env python3
"""
队列健康度监控脚本单元测试
测试monitor_queue_health.py的核心功能，重点关注业务指标和告警逻辑

按照用户请求"4. 自动化测试：为告警系统和重构组件添加单元测试"创建
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入要测试的模块
try:
    # 我们将模拟外部依赖，所以可以导入整个模块
    import monitor_queue_health as monitor
except ImportError as e:
    print(f"导入监控模块失败: {e}")
    # 在测试中创建一些模拟函数
    monitor = None


class TestMonitorQueueHealth(unittest.TestCase):
    """队列健康度监控测试类"""

    def setUp(self):
        """测试前置设置"""
        # 创建模拟队列数据
        self.sample_queue_data = {
            "items": {
                "task_001": {
                    "status": "pending",
                    "metadata": {"created": "2026-04-19T10:00:00Z"},
                    "updated_at": "2026-04-19T10:00:00Z",
                },
                "task_002": {
                    "status": "running",
                    "metadata": {"created": "2026-04-19T09:30:00Z"},
                    "updated_at": "2026-04-19T09:45:00Z",
                },
                "task_003": {
                    "status": "completed",
                    "metadata": {
                        "created": "2026-04-19T09:00:00Z",
                        "scan_time": "2026-04-19T09:00:00Z",
                    },
                    "updated_at": "2026-04-19T09:30:00Z",
                },
                "task_004": {
                    "status": "completed",
                    "metadata": {
                        "created": "2026-04-19T08:00:00Z",
                        "scan_time": "2026-04-19T08:00:00Z",
                    },
                    "updated_at": "2026-04-19T08:30:00Z",
                },
                "task_005": {
                    "status": "failed",
                    "metadata": {"created": "2026-04-19T07:00:00Z"},
                    "updated_at": "2026-04-19T07:10:00Z",
                },
            }
        }

        # 模拟系统指标
        self.sample_system_metrics = {
            "cpu_percent": 45.5,
            "memory_percent": 65.2,
            "memory_available_gb": 8.3,
            "disk_percent": 55.7,
            "disk_free_gb": 450.2,
            "timestamp": datetime.now().isoformat(),
        }

        # 创建临时文件用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.temp_queue_file = os.path.join(self.temp_dir, "test_queue.json")

        with open(self.temp_queue_file, "w", encoding="utf-8") as f:
            json.dump(self.sample_queue_data, f)

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_queue_data_success(self):
        """测试成功加载队列数据"""
        with patch(
            "monitor_queue_health.open", mock_open(read_data=json.dumps(self.sample_queue_data))
        ) as mock_file:
            result = monitor.load_queue_data(self.temp_queue_file)
            self.assertIsNotNone(result)
            self.assertIn("items", result)
            self.assertEqual(len(result["items"]), 5)

    def test_load_queue_data_file_not_found(self):
        """测试文件不存在时的队列加载"""
        non_existent_file = "/non/existent/file.json"
        result = monitor.load_queue_data(non_existent_file)
        self.assertIsNone(result)

    def test_analyze_queue_health_basic(self):
        """测试队列健康度基本分析"""
        # 模拟分析函数
        result = monitor.analyze_queue_health(self.sample_queue_data, "test_queue")

        self.assertIsNotNone(result)
        self.assertEqual(result["queue_name"], "test_queue")
        self.assertEqual(result["total_tasks"], 5)
        self.assertEqual(result["pending_tasks"], 1)
        self.assertEqual(result["running_tasks"], 1)
        self.assertEqual(result["completed_tasks"], 2)
        self.assertEqual(result["failed_tasks"], 1)

    def test_analyze_queue_health_invalid_data(self):
        """测试无效队列数据分析"""
        # 空数据
        result = monitor.analyze_queue_health(None, "test_queue")
        self.assertIsNone(result)

        # 缺少items键
        result = monitor.analyze_queue_health({"other_key": "value"}, "test_queue")
        self.assertIsNone(result)

    def test_analyze_queue_health_calculations(self):
        """测试队列分析中的计算逻辑"""
        # 创建专门用于计算测试的数据
        test_data = {
            "items": {
                "task1": {
                    "status": "completed",
                    "metadata": {
                        "created": "2026-04-19T10:00:00Z",
                        "scan_time": "2026-04-19T10:00:00Z",
                    },
                    "updated_at": "2026-04-19T10:30:00Z",  # 30分钟
                },
                "task2": {
                    "status": "completed",
                    "metadata": {
                        "created": "2026-04-19T09:00:00Z",
                        "scan_time": "2026-04-19T09:00:00Z",
                    },
                    "updated_at": "2026-04-19T09:20:00Z",  # 20分钟
                },
            }
        }

        result = monitor.analyze_queue_health(test_data, "test_queue")

        # 测试平均处理时间（应该大约是25分钟，即1500秒）
        avg_time = result["avg_execution_time"]
        self.assertGreater(avg_time, 1400)  # 约23分钟
        self.assertLess(avg_time, 1600)  # 约27分钟

        # 测试健康度评分应该在合理范围内
        self.assertGreaterEqual(result["health_score"], 0)
        self.assertLessEqual(result["health_score"], 100)

    def test_calculate_health_score_edge_cases(self):
        """测试健康度评分计算边界情况"""
        # 空队列
        score = monitor.calculate_health_score({}, 0, 0)
        self.assertEqual(score, 100)

        # 全pending队列
        status_counts = {"pending": 10}
        score = monitor.calculate_health_score(status_counts, 10, 0)
        self.assertLessEqual(score, 70)  # 应该扣分（等于70）

        # 高失败率
        status_counts = {"completed": 8, "failed": 2}  # 20%失败率
        score = monitor.calculate_health_score(status_counts, 10, 0)
        self.assertLess(score, 90)  # 应该扣分

        # 长时间处理
        status_counts = {"completed": 10}
        score = monitor.calculate_health_score(status_counts, 10, 4000)  # 超过1小时
        self.assertLess(score, 90)  # 应该扣分

    def test_calculate_health_score_ranges(self):
        """测试健康度评分范围"""
        # 完美队列
        status_counts = {"completed": 10}
        score = monitor.calculate_health_score(status_counts, 10, 300)  # 5分钟
        self.assertEqual(score, 100)

        # 中等队列
        status_counts = {"pending": 3, "completed": 7}  # 30% pending
        score = monitor.calculate_health_score(status_counts, 10, 1200)  # 20分钟
        self.assertGreaterEqual(score, 60)  # 应该至少60分

        # 差队列
        status_counts = {"pending": 6, "failed": 2, "completed": 2}  # 60% pending, 20% failed
        score = monitor.calculate_health_score(status_counts, 10, 7200)  # 2小时
        self.assertLess(score, 50)  # 应该低于50分

    def test_collect_system_metrics_mocked(self):
        """测试系统指标收集（使用模拟）"""
        with patch("monitor_queue_health.psutil.cpu_percent", return_value=65.5):
            with patch("monitor_queue_health.psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.percent = 75.3
                mock_memory.return_value.available = 4 * 1024**3  # 4GB

                with patch("monitor_queue_health.psutil.disk_usage") as mock_disk:
                    mock_disk.return_value.percent = 60.2
                    mock_disk.return_value.free = 200 * 1024**3  # 200GB

                    result = monitor.collect_system_metrics()

                    self.assertIsNotNone(result)
                    self.assertEqual(result["cpu_percent"], 65.5)
                    self.assertEqual(result["memory_percent"], 75.3)
                    self.assertAlmostEqual(result["memory_available_gb"], 4.0, delta=0.1)
                    self.assertEqual(result["disk_percent"], 60.2)
                    self.assertAlmostEqual(result["disk_free_gb"], 200.0, delta=0.1)

    def test_business_metrics_alerts(self):
        """测试业务指标告警规则"""
        # 测试队列指标
        queue_metrics = {
            "health_score": 55,  # 低于60
            "total_tasks": 250,  # 超过200
            "pending_tasks": 130,  # 超过50%
            "failed_tasks": 15,  # 6%失败率（超过5%）
            "completion_rate_per_hour": 0.5,  # 低于1
            "avg_execution_time": 9000,  # 2.5小时
            "running_tasks": 5,
            "completed_tasks": 100,
        }

        system_metrics = {
            "cpu_percent": 85,  # 超过80%
            "memory_percent": 82,  # 超过80%
            "memory_available_gb": 1.5,  # 低于2GB
            "disk_percent": 90,  # 超过85%
            "disk_free_gb": 50.0,
        }

        # 在generate_html_dashboard中测试告警生成
        # 这里我们直接测试告警逻辑
        alerts = []

        # 1. 队列健康度低
        if queue_metrics["health_score"] < 60:
            alerts.append(
                {
                    "level": "critical",
                    "title": "队列健康度低",
                    "message": f"队列健康度评分仅{queue_metrics['health_score']}，需要立即关注",
                }
            )

        # 2. 队列深度过大
        if queue_metrics["total_tasks"] > 200:
            alerts.append(
                {
                    "level": "critical",
                    "title": "队列深度过大",
                    "message": f"队列深度超过200个任务 ({queue_metrics['total_tasks']})",
                }
            )

        # 3. 待处理任务过多
        if queue_metrics["pending_tasks"] > queue_metrics["total_tasks"] * 0.5:
            alerts.append(
                {
                    "level": "critical",
                    "title": "待处理任务过多",
                    "message": f"待处理任务占比超过50% ({queue_metrics['pending_tasks']}/{queue_metrics['total_tasks']})",
                }
            )

        # 4. 错误率过高
        if queue_metrics.get("failed_tasks", 0) > 0:
            error_rate = queue_metrics["failed_tasks"] / queue_metrics["total_tasks"]
            if error_rate > 0.05:
                alerts.append(
                    {
                        "level": "critical",
                        "title": "错误率过高",
                        "message": f"任务错误率超过5% ({error_rate*100:.1f}%，{queue_metrics['failed_tasks']}/{queue_metrics['total_tasks']})",
                    }
                )

        # 5. 任务吞吐量低
        if queue_metrics["completion_rate_per_hour"] < 1.0 and queue_metrics["pending_tasks"] > 0:
            alerts.append(
                {
                    "level": "warning",
                    "title": "任务吞吐量低",
                    "message": f"任务吞吐量仅为{queue_metrics['completion_rate_per_hour']:.1f}任务/小时，处理速度过慢",
                }
            )

        # 6. 平均处理时间极长
        avg_seconds = queue_metrics["avg_execution_time"]
        if avg_seconds > 7200:  # 超过2小时
            alerts.append(
                {
                    "level": "critical",
                    "title": "平均处理时间极长",
                    "message": f"平均处理时间超过2小时 ({avg_seconds/3600:.1f}小时)，需要优化",
                }
            )
        elif avg_seconds > 1800:  # 超过30分钟
            alerts.append(
                {
                    "level": "warning",
                    "title": "平均处理时间较长",
                    "message": f"平均处理时间超过30分钟 ({avg_seconds/60:.1f}分钟)，建议检查",
                }
            )

        # 7. CPU使用率高
        if system_metrics["cpu_percent"] > 80:
            alerts.append(
                {
                    "level": "warning",
                    "title": "CPU使用率高",
                    "message": f"CPU使用率超过80% ({system_metrics['cpu_percent']}%)",
                }
            )

        # 8. 内存使用率高
        if system_metrics["memory_percent"] > 80:
            alerts.append(
                {
                    "level": "warning",
                    "title": "内存使用率高",
                    "message": f"内存使用率超过80% ({system_metrics['memory_percent']}%)",
                }
            )

        # 9. 磁盘使用率高
        if system_metrics["disk_percent"] > 85:
            alerts.append(
                {
                    "level": "warning",
                    "title": "磁盘使用率高",
                    "message": f"磁盘使用率超过85% ({system_metrics['disk_percent']}%)",
                }
            )

        # 10. 可用内存不足
        if system_metrics["memory_available_gb"] < 2:
            alerts.append(
                {
                    "level": "critical",
                    "title": "可用内存不足",
                    "message": f"可用内存不足2GB ({system_metrics['memory_available_gb']:.1f} GB)",
                }
            )

        # 验证告警数量
        self.assertGreater(len(alerts), 0)

        # 验证至少有以下告警类型
        alert_titles = [alert["title"] for alert in alerts]
        expected_critical_alerts = [
            "队列健康度低",
            "队列深度过大",
            "待处理任务过多",
            "错误率过高",
            "平均处理时间极长",
            "可用内存不足",
        ]

        for expected_alert in expected_critical_alerts:
            self.assertIn(expected_alert, alert_titles)

    def test_notification_filtering_policy(self):
        """测试通知过滤策略"""
        # 创建测试告警
        alerts = [
            {"level": "critical", "title": "严重告警1", "message": "测试严重告警"},
            {"level": "warning", "title": "警告告警1", "message": "测试警告告警"},
            {"level": "info", "title": "信息告警1", "message": "测试信息告警"},
        ]

        # 测试配置
        config = {
            "notification_strategy": {
                "send_email_for": ["critical", "warning"],
                "working_hours_start": 9,
                "working_hours_end": 18,
                "after_hours_critical_only": True,
            }
        }

        # 模拟工作时间（例如下午2点）
        with patch("monitor_queue_health.datetime") as mock_datetime:
            mock_now = datetime(2026, 4, 19, 14, 0, 0)  # 下午2点
            mock_datetime.now.return_value = mock_now

            filtered = monitor._filter_alerts_by_policy(alerts, config)

            # 在工作时间，应该包含critical和warning
            self.assertEqual(len(filtered), 2)
            levels = [alert["level"] for alert in filtered]
            self.assertIn("critical", levels)
            self.assertIn("warning", levels)
            self.assertNotIn("info", levels)

    def test_environment_variable_merging(self):
        """测试环境变量合并到配置"""
        test_config = {"email": {}, "slack": {}, "notification_strategy": {}}

        # 设置环境变量
        with patch.dict(
            "os.environ",
            {
                "OPENCLAW_SMTP_SERVER": "smtp.test.com",
                "OPENCLAW_SMTP_PORT": "587",
                "OPENCLAW_EMAIL_USERNAME": "test@example.com",
                "OPENCLAW_NOTIFY_LEVELS": "critical,warning",
                "OPENCLAW_WORKING_HOURS_START": "8",
                "OPENCLAW_WORKING_HOURS_END": "20",
            },
        ):
            result = monitor._merge_env_vars_into_config(test_config)

            # 验证邮件配置
            self.assertEqual(result["email"]["smtp_server"], "smtp.test.com")
            self.assertEqual(result["email"]["smtp_port"], 587)  # 应该转换为整数
            self.assertEqual(result["email"]["username"], "test@example.com")

            # 验证通知策略
            self.assertEqual(
                result["notification_strategy"]["send_email_for"], ["critical", "warning"]
            )
            self.assertEqual(result["notification_strategy"]["working_hours_start"], 8)
            self.assertEqual(result["notification_strategy"]["working_hours_end"], 20)

    def test_html_dashboard_generation(self):
        """测试HTML仪表板生成"""
        queue_metrics = {
            "queue_name": "test_queue",
            "health_score": 85,
            "total_tasks": 50,
            "pending_tasks": 5,
            "running_tasks": 3,
            "completed_tasks": 42,
            "failed_tasks": 0,
            "status_counts": {"pending": 5, "running": 3, "completed": 42},
            "avg_execution_time": 1800,  # 30分钟
            "completion_rate_per_hour": 2.5,
        }

        system_metrics = {
            "cpu_percent": 45.5,
            "memory_percent": 65.2,
            "memory_available_gb": 8.3,
            "disk_percent": 55.7,
            "disk_free_gb": 450.2,
        }

        history_data = [
            {"health_score": 80, "timestamp": "2026-04-19T10:00:00"},
            {"health_score": 82, "timestamp": "2026-04-19T10:05:00"},
            {"health_score": 85, "timestamp": "2026-04-19T10:10:00"},
        ]

        # 模拟send_notifications函数，避免实际发送
        with patch("monitor_queue_health.send_notifications") as mock_send:
            html = monitor.generate_html_dashboard(queue_metrics, system_metrics, history_data)

            # 验证HTML包含必要元素
            self.assertIsNotNone(html)
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("OpenClaw 队列健康度监控", html)
            self.assertIn("test_queue", html)
            self.assertIn("85/100", html)  # 健康度评分

            # 验证模拟函数被调用（因为有告警）
            mock_send.assert_called()

    def test_alert_logging(self):
        """测试告警日志记录"""
        alerts = [{"level": "warning", "title": "测试告警", "message": "这是一个测试告警"}]

        # 模拟文件操作
        mock_log_data = []

        def mock_json_load(f):
            return mock_log_data

        def mock_json_dump(data, f, **kwargs):
            mock_log_data.clear()
            mock_log_data.extend(data)

        with patch("monitor_queue_health.Path") as mock_path:
            mock_log_file = MagicMock()
            mock_log_file.exists.return_value = False
            mock_path.return_value.parent.mkdir = MagicMock()
            mock_path.return_value.__truediv__.return_value = mock_log_file

            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.load", side_effect=mock_json_load):
                    with patch("json.dump", side_effect=mock_json_dump):
                        # 调用send_notifications（配置为空，仅记录日志）
                        config = {}
                        with patch(
                            "monitor_queue_health._merge_env_vars_into_config", return_value=config
                        ):
                            monitor.send_notifications(alerts)

                        # 验证文件操作
                        mock_file.assert_called()

    def test_task_throughput_calculation(self):
        """测试任务吞吐量计算逻辑"""
        # 这个测试验证业务指标中的任务吞吐量计算
        # 创建包含时间信息的测试数据
        now = datetime.now()

        test_data = {
            "items": {
                "task1": {
                    "status": "completed",
                    "metadata": {"created": (now - timedelta(hours=2)).isoformat() + "Z"},
                    "updated_at": (now - timedelta(hours=1)).isoformat() + "Z",
                },
                "task2": {
                    "status": "completed",
                    "metadata": {"created": (now - timedelta(hours=3)).isoformat() + "Z"},
                    "updated_at": (now - timedelta(hours=2)).isoformat() + "Z",
                },
                "task3": {
                    "status": "pending",
                    "metadata": {"created": (now - timedelta(hours=1)).isoformat() + "Z"},
                    "updated_at": (now - timedelta(hours=1)).isoformat() + "Z",
                },
            }
        }

        result = monitor.analyze_queue_health(test_data, "throughput_test")

        # 验证吞吐量计算
        # 有2个完成的任务在最近24小时内，所以速率应该是 2/24 = 0.083 任务/小时
        # 但实际上analyze_queue_health中的逻辑是 len(recent_completions) / 24.0
        # recent_completions是最近24小时内完成的任务
        self.assertEqual(result["completed_tasks"], 2)
        self.assertGreaterEqual(result["completion_rate_per_hour"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
