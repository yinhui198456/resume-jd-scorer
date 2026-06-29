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
