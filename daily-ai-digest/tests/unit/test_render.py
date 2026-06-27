import json

from digest.generate.render import (
    compact_text,
    render_digest,
    render_fault_digest,
    render_feishu_post,
    render_feishu_section_posts,
)
from digest.models import DigestItem


def test_fault_digest_is_non_empty_and_actionable():
    output = render_fault_digest("run-1", "2026-06-22T08:46:00+08:00", [{"source_id": "openai-news", "error_code": "FETCH_TIMEOUT"}])
    assert "run-1" in output and "FETCH_TIMEOUT" in output
    assert "未复用历史资讯" in output


def test_normal_digest_keeps_source_link():
    digest_item = DigestItem("run-1", 1, "d1", ["n1"], "重点资讯", 1, "MCP 更新", "发布新版本", "影响工具集成", "en", "translated", ["https://example.com/a"], "2026-06-22T08:46:00+08:00")
    output = render_digest("run-1", "2026-06-22T08:46:00+08:00", {"重点资讯": [digest_item]}, {})
    assert "https://example.com/a" in output
    assert "候选池" in output


def test_compact_text_caps_output_at_100_characters():
    assert compact_text("甲" * 101) == "甲" * 99 + "…"
    assert len(compact_text("甲" * 101)) == 100


def test_feishu_post_is_compact_and_uses_one_link():
    item = DigestItem(
        "run-1", 1, "d1", ["n1"], "重点资讯", 1,
        "Codex 更新", "甲" * 110, "不应显示", "en", "translated",
        ["https://primary.example", "https://secondary.example"],
        "2026-06-24T08:45:00+08:00",
    )

    payload = render_feishu_post(
        "2026-06-24T08:45:00+08:00",
        {"重点资讯": [item], "候选池": []},
        {"status": "healthy", "failures": []},
    )

    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["zh_cn"]["title"] == "每日 AI 资讯｜6月24日"
    assert "甲" * 99 + "…" in serialized
    assert "https://primary.example" in serialized
    assert "https://secondary.example" not in serialized
    assert "不应显示" not in serialized
    assert "运行" not in serialized
    assert "候选速览" not in serialized
    assert not any(
        element.get("tag") == "text" and not element.get("text")
        for row in payload["zh_cn"]["content"]
        for element in row
    )


def test_feishu_post_renders_productivity_section():
    productivity = DigestItem(
        "run-1", 1, "d-productivity", ["n1"], "生产力项目", 1,
        "热门 Agent 项目", "新增工具链能力", "不应显示", "en", "translated",
        ["https://github.com/example/agent"],
        "2026-06-25T08:45:00+08:00",
    )

    payload = render_feishu_post(
        "2026-06-25T08:45:00+08:00",
        {"重点资讯": [], "生产力项目": [productivity]},
        {"status": "healthy", "failures": []},
    )

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "生产力项目" in serialized
    assert "热门 Agent 项目" in serialized
    assert "0 条重点 · 1 条生产力项目" in serialized


def test_feishu_post_keeps_fifteen_items_visible_in_compact_rows():
    sections = {}
    section_sizes = {"重点资讯": 6, "生产力项目": 9}
    for section, size in section_sizes.items():
        sections[section] = [
            DigestItem(
                "run-1", 1, f"{section}-{index}", [f"n-{section}-{index}"], section, index,
                f"{section}标题{index}", "这是一句完整但紧凑的说明", "不应显示",
                "en", "translated", [f"https://example.com/{section}/{index}"],
                "2026-06-25T08:45:00+08:00",
            )
            for index in range(1, size + 1)
        ]

    payload = render_feishu_post(
        "2026-06-25T08:45:00+08:00",
        sections,
        {"status": "healthy", "failures": []},
    )

    rows = payload["zh_cn"]["content"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert len(rows) <= 5
    assert serialized.count("查看原文") == 15
    assert "重点资讯标题6" in serialized
    assert "生产力项目标题9" in serialized
    assert "候选池" not in serialized


def test_feishu_section_posts_split_sections_into_separate_messages():
    sections = {}
    section_sizes = {"重点资讯": 6, "生产力项目": 9}
    for section, size in section_sizes.items():
        sections[section] = [
            DigestItem(
                "run-1", 1, f"{section}-{index}", [f"n-{section}-{index}"], section, index,
                f"{section}标题{index}", "这是一句完整但紧凑的说明", "不应显示",
                "en", "translated", [f"https://example.com/{section}/{index}"],
                "2026-06-25T08:45:00+08:00",
            )
            for index in range(1, size + 1)
        ]

    posts = render_feishu_section_posts(
        "2026-06-25T08:45:00+08:00",
        sections,
        {"status": "healthy", "failures": []},
    )

    assert len(posts) == 2
    assert [post["zh_cn"]["title"] for post in posts] == [
        "每日 AI 资讯｜6月25日｜重点资讯",
        "每日 AI 资讯｜6月25日｜生产力项目",
    ]
    assert [json.dumps(post, ensure_ascii=False).count("查看原文") for post in posts] == [6, 9]
