"""测试 parse_file.py 中的 extract_candidate_name 函数。

覆盖真实简历中的姓名提取场景：
- 正常格式：姓名:王洁玉
- OCR 噪声：名 ：袁永泉（前面带空格和噪声字符）
- 全角冒号：姓名：张三
- 无姓名：返回 None
- 空文本：返回 None
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills', 'resume-jd-scorer', 'scripts'))
from parse_file import extract_candidate_name


# ---- 正常场景 ----

def test_standard_colon_no_space():
    """标准格式：姓名:王洁玉（无空格，英文冒号）"""
    text = "姓名:王洁玉\n电话：15036630781"
    assert extract_candidate_name(text) == "王洁玉"


def test_standard_colon_with_space():
    """标准格式：姓名：张三（全角冒号）"""
    text = "姓名：张三\n学历：本科"
    assert extract_candidate_name(text) == "张三"


# ---- OCR 噪声场景 ----

def test_ocr_noise_before_name():
    """OCR 提取的文本中有噪声前缀：名 ：袁永泉"""
    text = "d3f6f101d1234f3e1HBz0ty8FFdYx4-8UvOZWOelmv7WPxBh Px\n名 ：袁永泉\n话：18236076646"
    assert extract_candidate_name(text) == "袁永泉"


def test_ocr_split_across_lines():
    """姓名标签和名字在不同行（OCR 断行）"""
    text = "姓名\n：王洁玉"
    assert extract_candidate_name(text) == "王洁玉"


def test_ocr_truncated_label():
    """只有"名"没有"姓"（OCR 截断）"""
    text = "名：沈建东\n电话：13800138000"
    assert extract_candidate_name(text) == "沈建东"


def test_ocr_with_garbage_chars():
    """姓名行前后有随机字符"""
    text = "xBhPx 姓名：李四 Wv7m\n邮箱：lisi@example.com"
    assert extract_candidate_name(text) == "李四"


# ---- 边界情况 ----

def test_empty_text():
    """空文本返回 None"""
    assert extract_candidate_name("") is None


def test_whitespace_only():
    """纯空白返回 None"""
    assert extract_candidate_name("   \n\n  ") is None


def test_no_name_pattern():
    """文本中没有姓名模式，返回 None"""
    text = "这是一段纯文本，没有姓名信息。\n只有普通内容。"
    assert extract_candidate_name(text) is None


def test_name_is_only_email():
    """"邮箱"不应被误识别为姓名"""
    text = "邮箱：test@example.com\n电话：13800138000"
    assert extract_candidate_name(text) is None


# ---- 多候选人场景 ----

def test_multiple_names_first_wins():
    """多个姓名模式时返回第一个"""
    text = "姓名：张三\n推荐人姓名：李四"
    result = extract_candidate_name(text)
    assert result == "张三"


def test_name_with_title():
    """姓名后有职务等文字，只提取名字部分（2-4个中文字）"""
    text = "姓名：王建国 | 大数据工程师\n公司：某科技公司"
    assert extract_candidate_name(text) == "王建国"


def test_single_char_name():
    """单字名也能识别"""
    text = "姓名：李\n年龄：25"
    assert extract_candidate_name(text) == "李"


def test_five_char_name_captures_first_four():
    """超过4个字时，正则贪婪匹配前4个字符"""
    text = "姓名：亚历山大陈\n电话：13800138000"
    assert extract_candidate_name(text) == "亚历山大"


def test_real_wangjieyu_resume():
    """真实王洁玉简历文本"""
    text = """B

Px

性别：女
电话：15036630781
工作年限：7 年

求职意向
意向岗位：大数据开发工程师

e65eb36c24ee049f1HF80tu1EVJSw4u7VvmbWOelmv7WPxBh

姓名:王洁玉

W
e65eb36c24ee049f1HF80tu1EVJSw4u7VvmbWOelmv7WPxBh
v7
年龄：28
邮箱：wjy12039625@163.com
"""
    assert extract_candidate_name(text) == "王洁玉"


def test_real_yuanyongquan_resume():
    """真实袁永泉简历 OCR 文本（含断行噪声）"""
    text = """d3f6f101d1234f3e1HBz0ty8FFdYx4-8UvOZWOelmv7WPxBh
d3f6f101d1234f3e1HBz0ty8FFdYx4-8UvOZWOelmv7WPxBh Px
名 ：袁永泉
话：18236076646
箱： 18236076646@163.com
校：南通理工学院
"""
    assert extract_candidate_name(text) == "袁永泉"
