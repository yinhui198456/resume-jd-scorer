from datetime import datetime

from digest.learn.models import LearningPlanCandidate, LearningPlanRow


def format_month(now: datetime) -> str:
    return f"{now.year} 年 {now.month} 月"


def direction_for(candidate: LearningPlanCandidate) -> str:
    text = f"{candidate.title} {candidate.summary} {candidate.url}".casefold()
    if any(
        keyword in text
        for keyword in ("claude code", "codex", "ai coding", "agentic coding", "coding", "code", "skill", "skills", "代码")
    ):
        return "Agentic Coding"
    if any(keyword in text for keyword in ("policy", "industry", "行业", "政策")):
        return "行业学习"
    if any(keyword in text for keyword in ("productivity", "note", "writing", "workflow", "生产力", "笔记", "写作")):
        return "综合能力"
    if any(keyword in text for keyword in ("server", "deploy", "proxy", "kubernetes", "基础设施")):
        return "基础设施"
    return "大模型"


def priority_for(user_intent: str) -> str:
    text = user_intent.casefold()
    if any(keyword in text for keyword in ("重点", "马上", "优先", "high")):
        return "高"
    if any(keyword in text for keyword in ("收藏", "有空", "备选", "low")):
        return "低"
    return "中"


def _task_name(candidate: LearningPlanCandidate) -> str:
    title = candidate.title.strip()
    if title.endswith("项目学习"):
        return title
    return f"{title} 项目学习"


def _output(candidate: LearningPlanCandidate) -> str:
    title = candidate.title.strip()
    return f"{title} 学习笔记 + 实践案例"


def _notes(candidate: LearningPlanCandidate) -> str:
    parts = [
        f"资讯关联：{candidate.source_date} 每日 AI 资讯",
        candidate.summary.strip(),
    ]
    if candidate.stars is not None:
        parts.append(f"GitHub {candidate.stars:,}⭐")
    return "；".join(part for part in parts if part)


def build_row(candidate: LearningPlanCandidate, task_id: str, now: datetime) -> LearningPlanRow:
    return LearningPlanRow(
        task_id=task_id,
        direction=direction_for(candidate),
        task_name=_task_name(candidate),
        output=_output(candidate),
        status="待开始",
        month=format_month(now),
        priority=priority_for(candidate.user_intent),
        notes=_notes(candidate),
        link=candidate.url.strip(),
    )
