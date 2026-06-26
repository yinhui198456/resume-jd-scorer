"""测试 save_jd.py 的 JD 持久化功能。

覆盖场景：
- 保存 JD → 加载 JD → 内容一致
- 覆盖保存（新 JD 替换旧 JD）
- 无保存文件时 load_jd 返回 None
- 损坏的 JSON 文件处理
- 来源信息记录（文件路径 / 手动输入）
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills', 'resume-jd-scorer', 'scripts'))


# 使用临时目录隔离测试
@pytest.fixture
def temp_data_dir(tmp_path):
    """为每个测试提供独立的数据目录。"""
    data_dir = tmp_path / "jd_data"
    data_dir.mkdir()
    # 临时修改 save_jd 模块的 DATA_DIR
    import save_jd
    original_dir = save_jd.DATA_DIR
    save_jd.DATA_DIR = str(data_dir)
    yield data_dir
    save_jd.DATA_DIR = original_dir


SAMPLE_JD = """
职位：AI Infra 平台运维工程师
地点：上海
薪资：11-18K

岗位职责：
1. 负责 GPU 算力集群的搭建与运维
2. 基于 Kubernetes 构建容器化平台底座
3. 支撑大模型训练推理业务的稳定运行

任职要求：
- 3 年+ Linux/K8s 运维经验
- 熟悉 NVIDIA GPU 集群管理
- 了解大模型训练基础设施
- 本科及以上学历
"""


def test_save_and_load_jd(temp_data_dir):
    """保存后加载，内容一致。"""
    from save_jd import save_jd, load_jd

    result = save_jd(SAMPLE_JD, source="test")
    assert result["success"] is True

    loaded = load_jd()
    assert loaded is not None
    assert loaded["jd_text"].strip() == SAMPLE_JD.strip()
    assert loaded["source"] == "test"
    assert "saved_at" in loaded


def test_load_without_save_returns_none(temp_data_dir):
    """未保存过 JD 时，load_jd 返回 None。"""
    from save_jd import load_jd

    assert load_jd() is None


def test_overwrite_jd(temp_data_dir):
    """新 JD 覆盖旧 JD。"""
    from save_jd import save_jd, load_jd

    save_jd("旧 JD 内容", source="old")
    save_jd("新 JD 内容", source="new")

    loaded = load_jd()
    assert loaded["jd_text"].strip() == "新 JD 内容"
    assert loaded["source"] == "new"


def test_save_records_char_count(temp_data_dir):
    """保存时记录字符数。"""
    from save_jd import save_jd, load_jd

    save_jd("12345", source="count_test")
    loaded = load_jd()
    assert loaded["char_count"] == 5


def test_save_from_file_path(temp_data_dir):
    """从文件路径保存，source 记录文件名。"""
    from save_jd import save_jd, load_jd

    save_jd(SAMPLE_JD, source="/path/to/ai_infra_jd.pdf")
    loaded = load_jd()
    assert loaded["source"] == "file:ai_infra_jd.pdf"


def test_corrupted_json_returns_none(temp_data_dir):
    """JSON 文件损坏时，load_jd 安全返回 None。"""
    from save_jd import load_jd
    import save_jd

    # 写入损坏的 JSON
    jd_file = os.path.join(save_jd.DATA_DIR, "current_jd.json")
    with open(jd_file, "w") as f:
        f.write("{invalid json")

    assert load_jd() is None


def test_empty_jd_text_rejected(temp_data_dir):
    """空 JD 文本保存失败。"""
    from save_jd import save_jd

    result = save_jd("", source="empty")
    assert result["success"] is False

    result = save_jd("   \n  ", source="whitespace")
    assert result["success"] is False


def test_has_jd_returns_correct_status(temp_data_dir):
    """has_jd() 正确反映保存状态。"""
    from save_jd import save_jd, has_jd

    assert has_jd() is False
    save_jd(SAMPLE_JD, source="test")
    assert has_jd() is True
