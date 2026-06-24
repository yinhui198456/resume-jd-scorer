import json

from digest.generate.render import (
    compact_text,
    render_digest,
    render_fault_digest,
    render_feishu_post,
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
