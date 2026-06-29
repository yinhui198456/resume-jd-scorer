#!/usr/bin/env python3
"""LLM-based next-week action inference for weekly report planning.

The online project tracking sheet does not have a dedicated "next week plan"
column. This module uses an LLM to infer a concrete PMO-style action target
from the task's stage, progress, plan dates and notes.

It is designed as an optional augmentation to the deterministic rule engine in
``report_engine_v9.py``. When the LLM call fails or returns an unusable result,
the caller should fall back to the existing rule-based inference.
"""
import json
import os
import re
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_TIMEOUT = 30
DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_MODEL_ENV = "MINIMAX_MODEL"
DEFAULT_API_KEY_ENV = "MINIMAX_API_KEY"


@dataclass(frozen=True, slots=True)
class NextWeekCandidate:
    """Input data for next-week action inference."""

    work_unit: str
    stage: str
    task: str
    progress: float
    status: str
    plan_start: str | None
    plan_end: str | None
    notes: str


class LLMNextWeekPlanner:
    """Call an OpenAI-compatible LLM to infer next-week actions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        session: Any = requests,
    ):
        self.api_key = api_key or os.environ.get(DEFAULT_API_KEY_ENV, "")
        self.model = model or os.environ.get(DEFAULT_MODEL_ENV, "MiniMax-M3")
        self.base_url = base_url.rstrip("/")
        self.session = session

    def _system_prompt(self) -> str:
        return (
            "你是一位严谨的项目管理办公室（PMO）文档助手。"
            "你的任务是根据项目跟进表中的一行任务数据，推断出下周应该采取的具体行动。"
            "输出必须简短、可执行、面向未来，不要复述当前状态。"
            "使用中文。直接返回行动描述，不要解释。"
        )

    def _user_prompt(self, candidate: NextWeekCandidate) -> str:
        progress_pct = int(candidate.progress * 100)
        lines = [
            "请根据以下任务信息推断下周行动：",
            f"工作单元：{candidate.work_unit or '未指定'}",
            f"任务阶段：{candidate.stage or '未指定'}",
            f"任务名称：{candidate.task or '未指定'}",
            f"当前进度：{progress_pct}%",
            f"状态：{candidate.status or '未指定'}",
        ]
        if candidate.plan_start:
            lines.append(f"计划开始：{candidate.plan_start}")
        if candidate.plan_end:
            lines.append(f"计划完成：{candidate.plan_end}")
        if candidate.notes:
            lines.append(f"备注：{candidate.notes}")
        lines.append(
            "要求："
            "1) 输出一句下周具体行动，格式类似'完成/启动/推进XXX，明确YYY'；"
            "2) 不要复述当前状态；"
            "3) 如果任务已接近截止日期，请强调跟踪风险；"
            "4) 总长度控制在 60 字以内。"
        )
        return "\n".join(lines)

    def _clean_response(self, text: str) -> str | None:
        text = text.strip().strip('"').strip("'")
        # Remove think blocks (some models emit reasoning tags)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # Remove common prefixes LLMs add
        text = re.sub(r"^(?:下周行动[：:]?|行动[：:]?|建议[：:]?)", "", text).strip()
        if len(text) < 5 or len(text) > 120:
            return None
        # Avoid responses that just repeat current status words
        if re.search(r"^(?:当前|目前|本周|已经)", text):
            return None
        return text

    def infer_action(self, candidate: NextWeekCandidate) -> str | None:
        """Return an inferred next-week action or None if LLM is unavailable."""
        if not self.api_key:
            return None

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": self._user_prompt(candidate)},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 120,
                },
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._clean_response(content)
        except Exception:
            return None


def infer_next_week_action_llm(
    work_unit: str,
    stage: str,
    task: str,
    progress: float,
    status: str,
    plan_start: str | None,
    plan_end: str | None,
    notes: str,
    planner: LLMNextWeekPlanner | None = None,
) -> str | None:
    """Convenience wrapper to infer a next-week action from raw row fields."""
    planner = planner or LLMNextWeekPlanner()
    candidate = NextWeekCandidate(
        work_unit=work_unit,
        stage=stage,
        task=task,
        progress=progress,
        status=status,
        plan_start=plan_start,
        plan_end=plan_end,
        notes=notes,
    )
    return planner.infer_action(candidate)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 llm_next_week_planner.py [work_unit] [stage] [task] [progress]")
        raise SystemExit(0)

    result = infer_next_week_action_llm(
        work_unit=sys.argv[1] if len(sys.argv) > 1 else "医共体运营管理驾驶舱",
        stage=sys.argv[2] if len(sys.argv) > 2 else "数据应用规划设计",
        task=sys.argv[3] if len(sys.argv) > 3 else "高保真设计",
        progress=float(sys.argv[4]) if len(sys.argv) > 4 else 0.9,
        status="进行中",
        plan_start=None,
        plan_end=None,
        notes="已与公卫进行沟通确认",
    )
    print(json.dumps({"action": result}, ensure_ascii=False))
