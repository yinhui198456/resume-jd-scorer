from datetime import datetime

from digest.models import DigestItem


SECTIONS = ["今日结论", "重点资讯", "Codex / CC 实践", "海外信号", "国内观察", "候选池"]


def compact_text(text: str, limit: int = 100) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def _link_line(label: str, url: str) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    if label:
        elements.append({"tag": "text", "text": label})
    if url:
        elements.append({"tag": "a", "text": "查看原文", "href": url})
    return elements


def render_feishu_post(
    generated_at: str,
    sections: dict[str, list[DigestItem]],
    source_health: dict[str, object],
) -> dict[str, object]:
    timestamp = datetime.fromisoformat(generated_at)
    top = sections.get("重点资讯", [])[:8]
    candidates = sections.get("候选池", [])[:3]
    health = "来源正常" if source_health.get("status") == "healthy" else "部分来源异常"
    content: list[list[dict[str, object]]] = [
        [{"tag": "text", "text": f"{health} · {len(top)} 条重点 · {len(candidates)} 条候选"}]
    ]
    for index, item in enumerate(top, 1):
        content.append(
            [{"tag": "text", "text": f"{index}. {item.chinese_title}", "style": ["bold"]}]
        )
        content.append([{"tag": "text", "text": compact_text(item.summary)}])
        content.append(_link_line("", item.source_links[0] if item.source_links else ""))
    if candidates:
        content.append([{"tag": "text", "text": "候选速览", "style": ["bold"]}])
        for item in candidates:
            content.append(
                _link_line(
                    f"• {item.chinese_title}  ",
                    item.source_links[0] if item.source_links else "",
                )
            )
    return {
        "zh_cn": {
            "title": f"每日 AI 资讯｜{timestamp.month}月{timestamp.day}日",
            "content": content,
        }
    }


def render_fault_digest(run_id: str, generated_at: str, failures: list[dict[str, str]]) -> str:
    lines = ["# 每日 AI 资讯故障简报", f"运行：{run_id}", f"时间：{generated_at}", "", "今日没有可用资讯；未复用历史资讯。", "", "## 失败来源"]
    lines.extend(f"- {item['source_id']}: {item['error_code']}" for item in failures)
    lines.extend(["", "请检查来源健康状态并使用原 run_id 重试。"])
    return "\n".join(lines) + "\n"


def render_digest(run_id: str, generated_at: str, sections: dict[str, list[DigestItem]], source_health: dict[str, object]) -> str:
    lines = ["# 每日 AI 资讯简报", f"运行：{run_id}", f"生成：{generated_at}"]
    for section in SECTIONS:
        lines.extend(["", f"## {section}"])
        items = sections.get(section, [])
        if not items:
            lines.append("- 无")
            continue
        for item in items:
            lines.extend([f"- {item.chinese_title}", f"  - 一句话：{item.summary}", f"  - 为什么重要：{item.why_it_matters}"])
            lines.extend(f"  - 来源：{url}" for url in item.source_links)
    return "\n".join(lines) + "\n"
