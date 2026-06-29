#!/usr/bin/env python3
"""Tests for llm_next_week_planner.py."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_next_week_planner import (
    LLMNextWeekPlanner,
    NextWeekCandidate,
    infer_next_week_action_llm,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP_{self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response_payload=None, status_code=200, raise_on_call=False):
        self.calls = []
        self.response_payload = response_payload or {
            "choices": [{"message": {"content": "完成高保真设计评审并同步相关方"}}]
        }
        self.status_code = status_code
        self.raise_on_call = raise_on_call

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.raise_on_call:
            raise RuntimeError("network error")
        return FakeResponse(self.response_payload, self.status_code)


def test_planner_returns_cleaned_action():
    session = FakeSession()
    planner = LLMNextWeekPlanner(api_key="test-key", model="qwen-test", session=session)
    candidate = NextWeekCandidate(
        work_unit="医共体",
        stage="设计",
        task="高保真",
        progress=0.9,
        status="进行中",
        plan_start=None,
        plan_end=None,
        notes="已与公卫沟通",
    )
    result = planner.infer_action(candidate)
    assert result == "完成高保真设计评审并同步相关方"
    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url.endswith("/chat/completions")
    assert kwargs["json"]["model"] == "qwen-test"


def test_planner_returns_none_without_api_key():
    session = FakeSession()
    planner = LLMNextWeekPlanner(api_key="", session=session)
    candidate = NextWeekCandidate(
        work_unit="医共体", stage="设计", task="高保真", progress=0.9,
        status="进行中", plan_start=None, plan_end=None, notes="",
    )
    assert planner.infer_action(candidate) is None
    assert len(session.calls) == 0


def test_planner_returns_none_on_network_error():
    session = FakeSession(raise_on_call=True)
    planner = LLMNextWeekPlanner(api_key="test-key", session=session)
    candidate = NextWeekCandidate(
        work_unit="医共体", stage="设计", task="高保真", progress=0.9,
        status="进行中", plan_start=None, plan_end=None, notes="",
    )
    assert planner.infer_action(candidate) is None


def test_planner_returns_none_for_short_response():
    session = FakeSession({"choices": [{"message": {"content": "OK"}}]})
    planner = LLMNextWeekPlanner(api_key="test-key", session=session)
    candidate = NextWeekCandidate(
        work_unit="医共体", stage="设计", task="高保真", progress=0.9,
        status="进行中", plan_start=None, plan_end=None, notes="",
    )
    assert planner.infer_action(candidate) is None


def test_wrapper_uses_default_planner():
    session = FakeSession()
    planner = LLMNextWeekPlanner(api_key="test-key", session=session)
    result = infer_next_week_action_llm(
        work_unit="医共体",
        stage="设计",
        task="高保真",
        progress=0.9,
        status="进行中",
        plan_start=None,
        plan_end=None,
        notes="",
        planner=planner,
    )
    assert result == "完成高保真设计评审并同步相关方"


def test_response_cleaning_strips_prefixes():
    session = FakeSession({"choices": [{"message": {"content": "下周行动：完成评审并同步"}}]})
    planner = LLMNextWeekPlanner(api_key="test-key", session=session)
    candidate = NextWeekCandidate(
        work_unit="医共体", stage="设计", task="高保真", progress=0.9,
        status="进行中", plan_start=None, plan_end=None, notes="",
    )
    assert planner.infer_action(candidate) == "完成评审并同步"


if __name__ == "__main__":
    raise SystemExit(0)
