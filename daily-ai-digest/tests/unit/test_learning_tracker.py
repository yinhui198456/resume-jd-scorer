from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from digest.learn.models import LearningPlanCandidate
from digest.learn.tracker import find_duplicate, next_task_id, plan_learning_write, validate_headers


HEADER = ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"]


def candidate():
    return LearningPlanCandidate(
        source_date="2026-06-29",
        title="Graphify",
        summary="将代码和文档转为知识图谱。",
        url="https://github.com/safishamsi/graphify",
        section="生产力项目",
        stars=5154,
        user_intent="感兴趣",
    )


def test_validate_headers_accepts_main_task_schema():
    validate_headers([HEADER])


def test_validate_headers_rejects_mismatch():
    with pytest.raises(ValueError, match="LEARNING_PLAN_HEADER_MISMATCH"):
        validate_headers([["任务序号", "方向", "错误"]])


def test_next_task_id_preserves_gaps():
    values = [
        HEADER,
        ["L01"],
        ["L02"],
        ["L04"],
        ["L35"],
    ]

    assert next_task_id(values) == "L36"


def test_find_duplicate_by_link():
    values = [
        HEADER,
        ["L35", "Agentic Coding", "Graphify 项目学习", "", "待开始", "", "中", "", "https://github.com/safishamsi/graphify"],
    ]

    duplicate = find_duplicate(values, candidate())

    assert duplicate is not None
    assert duplicate[0] == 2


def test_plan_append_for_new_candidate():
    now = datetime(2026, 6, 29, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    values = [HEADER, ["L35", "大模型", "Existing", "", "待开始", "", "中", "", ""]]

    plan = plan_learning_write(values, candidate(), now)

    assert plan.action == "append"
    assert plan.range_name == "A:I"
    assert plan.values[0][0] == "L36"
    assert plan.message == "准备记录：L36｜Agentic Coding｜Graphify 项目学习｜优先级：中｜状态：待开始。确认写入？"


def test_plan_update_for_duplicate_only_updates_notes_and_empty_link():
    now = datetime(2026, 6, 29, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    values = [
        HEADER,
        ["L35", "Agentic Coding", "Graphify 项目学习", "手工输出", "进行中", "", "高", "原备注", "https://github.com/safishamsi/graphify"],
    ]

    plan = plan_learning_write(values, candidate(), now)

    assert plan.action == "update"
    assert plan.range_name == "H2:I2"
    assert plan.existing_task_id == "L35"
    assert plan.values == [["原备注；再次出现：2026-06-29 每日 AI 资讯", "https://github.com/safishamsi/graphify"]]
