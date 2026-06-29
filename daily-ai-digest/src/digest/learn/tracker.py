import re
from datetime import datetime

from digest.learn.mapper import build_row
from digest.learn.models import SHEET_HEADERS, LearningPlanCandidate, LearningPlanWritePlan


def _cell(row: list[object], index: int) -> str:
    if len(row) <= index or row[index] is None:
        return ""
    value = row[index]
    if isinstance(value, list):
        return " ".join(
            str(part.get("link") or part.get("text") or "") if isinstance(part, dict) else str(part)
            for part in value
        )
    return str(value)


def cell_text(row: list[object], index: int) -> str:
    return _cell(row, index)


def validate_headers(values: list[list[object]]) -> None:
    if not values or tuple(str(value) for value in values[0][: len(SHEET_HEADERS)]) != SHEET_HEADERS:
        raise ValueError("LEARNING_PLAN_HEADER_MISMATCH")


def next_task_id(values: list[list[object]]) -> str:
    max_id = 0
    for row in values[1:]:
        match = re.fullmatch(r"L(\d+)", _cell(row, 0).strip())
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"L{max_id + 1:02d}"


def find_duplicate(values: list[list[object]], candidate: LearningPlanCandidate) -> tuple[int, list[object]] | None:
    target_url = candidate.url.strip()
    target_title = candidate.title.strip().casefold()
    for row_number, row in enumerate(values[1:], start=2):
        link = _cell(row, 8)
        task_name = _cell(row, 2).casefold()
        notes = _cell(row, 7).casefold()
        if target_url and target_url in link:
            return row_number, row
        if target_title and target_title in task_name:
            return row_number, row
        if target_title and target_title in notes:
            return row_number, row
    return None


def _append_source_note(notes: str, source_date: str) -> str:
    addition = f"再次出现：{source_date} 每日 AI 资讯"
    if addition in notes:
        return notes
    return f"{notes}；{addition}" if notes else addition


def plan_learning_write(
    values: list[list[object]],
    candidate: LearningPlanCandidate,
    now: datetime,
) -> LearningPlanWritePlan:
    validate_headers(values)
    duplicate = find_duplicate(values, candidate)
    if duplicate:
        row_number, row = duplicate
        task_id = _cell(row, 0)
        notes = _append_source_note(_cell(row, 7), candidate.source_date)
        link = _cell(row, 8)
        if link:
            return LearningPlanWritePlan(
                action="update",
                range_name=f"H{row_number}:H{row_number}",
                values=[[notes]],
                message=f"已更新已有任务：{task_id}｜{_cell(row, 2)}｜补充来源到备注",
                existing_task_id=task_id,
            )
        return LearningPlanWritePlan(
            action="update",
            range_name=f"H{row_number}:I{row_number}",
            values=[[notes, candidate.url]],
            message=f"已更新已有任务：{task_id}｜{_cell(row, 2)}｜补充来源到备注",
            existing_task_id=task_id,
        )

    task_id = next_task_id(values)
    row = build_row(candidate, task_id, now)
    return LearningPlanWritePlan(
        action="append",
        range_name="A:I",
        values=[row.to_values()],
        message=f"准备记录：{row.task_id}｜{row.direction}｜{row.task_name}｜优先级：{row.priority}｜状态：{row.status}。确认写入？",
    )
