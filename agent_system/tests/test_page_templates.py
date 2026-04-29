"""
Test Page Templates - Phase 12

测试页面模板库功能
"""

import os
import sys
import unittest

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state.page_templates import (
    PAGE_TEMPLATES,
    PageTemplate,
    get_all_templates,
    get_supported_states,
    get_target_state_from_task,
    get_template,
)


class TestPageTemplates(unittest.TestCase):
    """测试页面模板"""

    def test_all_templates_defined(self):
        """测试所有模板都已定义"""
        expected_states = [
            "home_screen",
            "settings_home",
            "settings_wifi",
            "settings_bluetooth",
            "browser_home",
            "search_page",
        ]

        for state in expected_states:
            self.assertIn(state, PAGE_TEMPLATES, f"模板 {state} 未定义")

    def test_template_structure(self):
        """测试模板结构"""
        for state, template in PAGE_TEMPLATES.items():
            self.assertIsInstance(template, PageTemplate)
            self.assertEqual(template.state, state)
            self.assertIsInstance(template.required_keywords, list)
            self.assertIsInstance(template.optional_keywords, list)
            self.assertIsInstance(template.negative_keywords, list)
            self.assertIsInstance(template.ui_hints, list)
            self.assertGreater(template.min_score, 0)

    def test_settings_wifi_template(self):
        """测试 Wi-Fi 模板"""
        template = get_template("settings_wifi")

        self.assertIn("Wi-Fi", template.required_keywords)
        self.assertIn("WLAN", template.required_keywords)
        self.assertIn("网络", template.optional_keywords)
        self.assertIn("开关", template.optional_keywords)
        self.assertIn("蓝牙", template.negative_keywords)
        self.assertIn("toggle", template.ui_hints)

    def test_settings_bluetooth_template(self):
        """测试蓝牙模板"""
        template = get_template("settings_bluetooth")

        self.assertIn("蓝牙", template.required_keywords)
        self.assertIn("设备", template.optional_keywords)
        self.assertIn("Wi-Fi", template.negative_keywords)
        self.assertIn("toggle", template.ui_hints)

    def test_search_page_template(self):
        """测试搜索页模板"""
        template = get_template("search_page")

        self.assertIn("搜索", template.required_keywords)
        self.assertIn("输入", template.required_keywords)
        self.assertIn("建议", template.optional_keywords)
        self.assertIn("search_input", template.ui_hints)

    def test_get_supported_states(self):
        """测试获取支持的状态列表"""
        states = get_supported_states()

        self.assertIn("home_screen", states)
        self.assertIn("settings_home", states)
        self.assertIn("settings_wifi", states)
        self.assertIn("settings_bluetooth", states)
        self.assertIn("browser_home", states)
        self.assertIn("search_page", states)

    def test_task_target_mapping(self):
        """测试任务到目标状态的映射"""
        # Wi-Fi 任务
        self.assertEqual(get_target_state_from_task("打开 Wi-Fi"), "settings_wifi")
        self.assertEqual(get_target_state_from_task("打开无线网络"), "settings_wifi")
        self.assertEqual(get_target_state_from_task("打开 WLAN"), "settings_wifi")

        # 蓝牙任务
        self.assertEqual(get_target_state_from_task("打开蓝牙"), "settings_bluetooth")
        self.assertEqual(get_target_state_from_task("打开 Bluetooth"), "settings_bluetooth")

        # 搜索任务
        self.assertEqual(get_target_state_from_task("点击搜索"), "search_page")
        self.assertEqual(get_target_state_from_task("打开搜索"), "search_page")
        self.assertEqual(get_target_state_from_task("搜索"), "search_page")

        # 未知任务
        self.assertIsNone(get_target_state_from_task("未知任务"))

    def test_negative_keywords(self):
        """测试负向关键词"""
        wifi_template = get_template("settings_wifi")
        bt_template = get_template("settings_bluetooth")

        # Wi-Fi 页面不应该有蓝牙关键词
        self.assertIn("蓝牙", wifi_template.negative_keywords)

        # 蓝牙页面不应该有 Wi-Fi 关键词
        self.assertIn("Wi-Fi", bt_template.negative_keywords)


if __name__ == "__main__":
    unittest.main()
