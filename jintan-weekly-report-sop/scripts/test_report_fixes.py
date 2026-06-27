#!/usr/bin/env python3
"""
TDD Tests for v5 report engine QA fixes.
Tests run BEFORE implementation — must FAIL initially.
"""
import unittest
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the module we're testing — MUST fail if not implemented (RED phase)
from project_report import (
    sanitize_note_text,
    is_external_blocked,
    clean_placeholder_text,
    format_with_numbering,
)


class TestSanitizeNoteText(unittest.TestCase):
    """测试1: "进行中" → "尚未完成" + 剥离日期前缀"""

    def test_in_progress_replaced(self):
        """进行中 should be replaced with 尚未完成"""
        result = sanitize_note_text("卫宁数据开发进行中，需要提供数据字典")
        self.assertIn("尚未完成", result)
        self.assertNotIn("进行中", result)

    def test_date_prefix_stripped(self):
        """日期前缀如 0611: 应被剥离"""
        result = sanitize_note_text("0611：卫宁数据开发进行中")
        self.assertFalse(result.startswith("0611"))
        self.assertNotIn("0611", result)

    def test_multi_date_latest_extracted(self):
        """多日期备注应提取最新的"""
        result = sanitize_note_text("0428:旧内容|0611:新内容")
        self.assertIn("新内容", result)

    def test_no_change_when_clean(self):
        """干净文本不应被修改"""
        result = sanitize_note_text("已完成接口对接")
        self.assertEqual(result, "已完成接口对接")

    def test_empty_input(self):
        """空输入返回空"""
        self.assertEqual(sanitize_note_text(""), "")
        self.assertEqual(sanitize_note_text(None), "")


class TestExternalBlocked(unittest.TestCase):
    """测试2: 第三方阻塞项白名单（跳过量化检查）"""

    def test_external_blocked_pattern_1(self):
        """尚未完成...需要提供 应识别为外部阻塞"""
        text = "卫宁数据开发尚未完成，需要提供数据字典"
        self.assertTrue(is_external_blocked(text))

    def test_external_blocked_pattern_2(self):
        """需要...提供...数据 应识别为外部阻塞"""
        text = "需要提供源数据才能继续"
        self.assertTrue(is_external_blocked(text))

    def test_external_blocked_pattern_3(self):
        """等待...反馈 应识别为外部阻塞"""
        text = "等待业务方反馈确认"
        self.assertTrue(is_external_blocked(text))

    def test_not_blocked_normal_task(self):
        """正常任务不应被误判"""
        text = "数据清洗完成80%"
        self.assertFalse(is_external_blocked(text))

    def test_not_blocked_ongoing(self):
        """单纯进行中不是外部阻塞"""
        text = "接口开发进行中"
        self.assertFalse(is_external_blocked(text))


class TestCleanPlaceholder(unittest.TestCase):
    """测试3: 模板占位文字清理"""

    def test_remove_placeholder_risk(self):
        """预计存在或可能出现的风险及解决方案 应被清理"""
        text = "预计存在或可能出现的风险及解决方案"
        result = clean_placeholder_text(text)
        self.assertEqual(result, "")

    def test_remove_placeholder_empty(self):
        """预计存在 应被清理"""
        text = "预计存在"
        result = clean_placeholder_text(text)
        self.assertEqual(result, "")

    def test_keep_real_content(self):
        """真实内容应保留"""
        text = "卫宁数据接口尚未完成"
        result = clean_placeholder_text(text)
        self.assertEqual(result, text)

    def test_partial_placeholder_removed(self):
        """包含占位文字的行应清理占位部分"""
        text = "暂无。预计存在或可能出现的风险及解决方案"
        result = clean_placeholder_text(text)
        self.assertNotIn("预计存在", result)


class TestNumbering(unittest.TestCase):
    """测试4: 编号格式（一级中文、二级阿拉伯）"""

    def test_level1_chinese_numbering(self):
        """一级标题应使用中文编号"""
        items = [
            {"type": "unit", "text": "数据应用规划设计"},
            {"type": "task", "text": "调研工作"},
        ]
        result = format_with_numbering(items)
        self.assertTrue(any("一、" in str(item) for item in result))

    def test_level2_decimal_numbering(self):
        """二级标题应使用阿拉伯数字编号"""
        items = [
            {"type": "unit", "text": "数据应用"},
            {"type": "stage", "text": "调研与需求分析"},
            {"type": "task", "text": "任务A"},
        ]
        result = format_with_numbering(items)
        # Check that stage has decimal numbering like "1."
        stage_items = [i for i in result if i.get("type") == "stage"]
        if stage_items:
            self.assertTrue(any("1." in str(i.get("text", "")) for i in stage_items))

    def test_empty_items(self):
        """空列表应返回空列表"""
        self.assertEqual(format_with_numbering([]), [])


class TestQuantificationWhitelist(unittest.TestCase):
    """测试5: 量化检查白名单 — 第三方阻塞项跳过量化检查"""

    def test_external_block_skipped(self):
        """外部阻塞项不应触发量化 FAIL"""
        from validate_report_tone import check_quantification
        text = "• Smartbi前端可视化大屏与地图组件开发：卫宁数据开发尚未完成，需要提供数据字典给smartbi"
        issues = check_quantification(text)
        self.assertEqual(issues, [])

    def test_normal_task_still_checked(self):
        """正常任务仍应触发量化检查"""
        from validate_report_tone import check_quantification
        text = "• 数据准确性比对与性能压力测试"
        issues = check_quantification(text)
        self.assertTrue(len(issues) > 0)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
