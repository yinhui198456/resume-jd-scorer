from datetime import datetime
from zoneinfo import ZoneInfo

from digest.learn.mapper import build_row, direction_for, format_month, priority_for
from digest.learn.models import SHEET_HEADERS, LearningPlanCandidate


def test_sheet_headers_match_main_task_schema():
    assert SHEET_HEADERS == (
        "任务序号",
        "方向",
        "任务项",
        "输出",
        "状态",
        "月份",
        "优先级",
        "备注",
        "链接",
    )


def test_learning_plan_candidate_is_plain_data():
    candidate = LearningPlanCandidate(
        source_date="2026-06-29",
        title="Graphify",
        summary="将代码和文档转为知识图谱。",
        url="https://github.com/safishamsi/graphify",
        section="生产力项目",
        stars=5154,
        user_intent="感兴趣",
    )

    assert candidate.title == "Graphify"
    assert candidate.stars == 5154


def test_format_month_uses_chinese_year_month():
    now = datetime(2026, 6, 29, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert format_month(now) == "2026 年 6 月"


def test_direction_mapping_for_agentic_coding():
    candidate = LearningPlanCandidate(
        source_date="2026-06-29",
        title="Codex Skills",
        summary="AI coding workflow skill.",
        url="https://github.com/example/skills",
        section="生产力项目",
        stars=100,
        user_intent="记录一下",
    )

    assert direction_for(candidate) == "Agentic Coding"


def test_priority_mapping_from_user_intent():
    assert priority_for("重点关注") == "高"
    assert priority_for("记录一下") == "中"
    assert priority_for("先收藏") == "低"


def test_build_row_for_github_project():
    now = datetime(2026, 6, 29, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    candidate = LearningPlanCandidate(
        source_date="2026-06-29",
        title="Graphify",
        summary="将代码和文档转为知识图谱。",
        url="https://github.com/safishamsi/graphify",
        section="生产力项目",
        stars=5154,
        user_intent="感兴趣",
    )

    row = build_row(candidate, "L36", now)

    assert row.to_values() == [
        "L36",
        "Agentic Coding",
        "Graphify 项目学习",
        "Graphify 学习笔记 + 实践案例",
        "待开始",
        "2026 年 6 月",
        "中",
        "资讯关联：2026-06-29 每日 AI 资讯；将代码和文档转为知识图谱。；GitHub 5,154⭐",
        "https://github.com/safishamsi/graphify",
    ]
