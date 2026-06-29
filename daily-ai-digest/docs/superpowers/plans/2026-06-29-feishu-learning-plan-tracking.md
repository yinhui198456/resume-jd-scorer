# Feishu Learning Plan Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-confirmed workflow that records selected Daily AI Digest items into the Feishu spreadsheet `学习计划追踪 2026` sheet `主任务`.

**Architecture:** Add a focused Feishu Sheets client, a learning-plan mapping/deduplication layer, and a small CLI entry point for preview/write operations. Keep this separate from the existing Feishu group-message delivery path; daily digest generation remains unchanged except that generated digest JSON can be used as input to the new tracker workflow.

**Tech Stack:** Python 3.12, pytest, requests, Feishu Sheets API behind a local client abstraction, existing `AppConfig` environment loading.

## Global Constraints

- Target spreadsheet token: `R4LAsRmQKhfMXYtV7UacSeaGngg`.
- Target sheet title: `主任务`.
- Target sheet id: `349176`.
- Target columns are A-I only: `任务序号`, `方向`, `任务项`, `输出`, `状态`, `月份`, `优先级`, `备注`, `链接`.
- Do not touch columns J-T.
- Do not use Feishu Bitable APIs.
- Do not automatically record all digest items.
- Do not write to the spreadsheet without explicit user confirmation.
- Do not overwrite user-managed `状态`, `优先级`, `任务项`, or `输出` on duplicate rows.
- Do not log `app_secret` or tenant access tokens.
- Real Feishu write smoke tests require explicit user approval.

---

## File Structure

- Create `src/digest/learn/__init__.py`: package marker for learning-plan tracking.
- Create `src/digest/learn/models.py`: dataclasses for sheet rows, candidate records, write plans, and write results.
- Create `src/digest/learn/mapper.py`: pure mapping functions from digest item data and user intent to target sheet row values.
- Create `src/digest/learn/sheets.py`: Feishu Sheets client using app credentials and tenant token; no digest-specific logic.
- Create `src/digest/learn/tracker.py`: orchestration layer for read/validate/deduplicate/preview/write.
- Create `src/digest/jobs/learning_plan.py`: CLI for previewing or applying one learning-plan record.
- Modify `src/digest/models.py`: add optional learning-plan environment fields only if needed by config loading.
- Modify `src/digest/config.py`: load optional `DAILY_AI_DIGEST_LEARNING_PLAN_SPREADSHEET_TOKEN` and `DAILY_AI_DIGEST_LEARNING_PLAN_SHEET_TITLE` with defaults from the spec.
- Create `tests/unit/test_learning_mapper.py`: pure mapping tests.
- Create `tests/unit/test_learning_tracker.py`: dedupe, next-id, header validation, payload tests.
- Create `tests/unit/test_feishu_sheets.py`: Feishu Sheets API request/response tests with fake sessions.
- Create `tests/integration/test_learning_plan_cli.py`: CLI preview/apply tests using fake client dependencies.
- Modify `docs/operations.md`: document how to preview and apply a learning-plan record.

---

### Task 1: Add learning-plan data models

**Files:**
- Create: `src/digest/learn/__init__.py`
- Create: `src/digest/learn/models.py`
- Test: `tests/unit/test_learning_mapper.py`

**Interfaces:**
- Produces:
  - `SHEET_HEADERS: tuple[str, ...]`
  - `LearningPlanRow`
  - `LearningPlanCandidate`
  - `LearningPlanWritePlan`
  - `LearningPlanWriteResult`

- [ ] **Step 1: Create package marker**

Create `src/digest/learn/__init__.py`:

```python
"""Learning-plan tracking for Daily AI Digest."""
```

- [ ] **Step 2: Write the failing model/header test**

Create `tests/unit/test_learning_mapper.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_mapper.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'digest.learn'`.

- [ ] **Step 4: Implement models**

Create `src/digest/learn/models.py`:

```python
from dataclasses import dataclass


SHEET_HEADERS = (
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


@dataclass(frozen=True, slots=True)
class LearningPlanCandidate:
    source_date: str
    title: str
    summary: str
    url: str
    section: str
    stars: int | None
    user_intent: str


@dataclass(frozen=True, slots=True)
class LearningPlanRow:
    task_id: str
    direction: str
    task_name: str
    output: str
    status: str
    month: str
    priority: str
    notes: str
    link: str

    def to_values(self) -> list[str]:
        return [
            self.task_id,
            self.direction,
            self.task_name,
            self.output,
            self.status,
            self.month,
            self.priority,
            self.notes,
            self.link,
        ]


@dataclass(frozen=True, slots=True)
class LearningPlanWritePlan:
    action: str
    range_name: str
    values: list[list[str]]
    message: str
    existing_task_id: str | None = None


@dataclass(frozen=True, slots=True)
class LearningPlanWriteResult:
    action: str
    task_id: str
    status: str
    message: str
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_mapper.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/digest/learn/__init__.py src/digest/learn/models.py tests/unit/test_learning_mapper.py
git commit -m "feat(digest): add learning plan data models"
```

---

### Task 2: Implement deterministic row mapping

**Files:**
- Create: `src/digest/learn/mapper.py`
- Modify: `tests/unit/test_learning_mapper.py`

**Interfaces:**
- Consumes:
  - `LearningPlanCandidate`
  - `LearningPlanRow`
- Produces:
  - `format_month(now: datetime) -> str`
  - `direction_for(candidate: LearningPlanCandidate) -> str`
  - `priority_for(user_intent: str) -> str`
  - `build_row(candidate: LearningPlanCandidate, task_id: str, now: datetime) -> LearningPlanRow`

- [ ] **Step 1: Add failing mapping tests**

Append to `tests/unit/test_learning_mapper.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from digest.learn.mapper import build_row, direction_for, format_month, priority_for


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_mapper.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'digest.learn.mapper'`.

- [ ] **Step 3: Implement mapper**

Create `src/digest/learn/mapper.py`:

```python
from datetime import datetime

from digest.learn.models import LearningPlanCandidate, LearningPlanRow


def format_month(now: datetime) -> str:
    return f"{now.year} 年 {now.month} 月"


def direction_for(candidate: LearningPlanCandidate) -> str:
    text = f"{candidate.title} {candidate.summary} {candidate.url}".casefold()
    if any(keyword in text for keyword in ("claude code", "codex", "ai coding", "agentic coding", "skill", "skills")):
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
```

- [ ] **Step 4: Run mapper tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_mapper.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/digest/learn/mapper.py tests/unit/test_learning_mapper.py
git commit -m "feat(digest): map digest interests to learning plan rows"
```

---

### Task 3: Build Feishu Sheets client

**Files:**
- Create: `src/digest/learn/sheets.py`
- Create: `tests/unit/test_feishu_sheets.py`

**Interfaces:**
- Produces:
  - `FeishuSheetsClient(app_id: str, app_secret: str, session=requests)`
  - `get_tenant_token() -> str`
  - `get_sheets(spreadsheet_token: str) -> list[dict[str, object]]`
  - `read_values(spreadsheet_token: str, sheet_id: str, range_name: str) -> list[list[object]]`
  - `append_values(spreadsheet_token: str, sheet_id: str, range_name: str, values: list[list[object]]) -> dict[str, object]`
  - `update_values(spreadsheet_token: str, sheet_id: str, range_name: str, values: list[list[object]]) -> dict[str, object]`

- [ ] **Step 1: Write failing API tests**

Create `tests/unit/test_feishu_sheets.py`:

```python
from digest.learn.sheets import FeishuSheetsClient


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
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/auth/v3/tenant_access_token/internal"):
            return FakeResponse({"code": 0, "tenant_access_token": "tenant-token"})
        return FakeResponse({"code": 0, "data": {"updatedRange": "349176!A36:I36"}})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url.endswith("/sheets/query"):
            return FakeResponse({"code": 0, "data": {"sheets": [{"sheet_id": "349176", "title": "主任务"}]}})
        return FakeResponse({"code": 0, "data": {"valueRange": {"values": [["任务序号"]]}}})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        return FakeResponse({"code": 0, "data": {"updatedRange": "349176!H36:I36"}})


def test_get_sheets_uses_v3_query_endpoint():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    sheets = client.get_sheets("spreadsheet-token")

    assert sheets == [{"sheet_id": "349176", "title": "主任务"}]
    method, url, kwargs = session.calls[-1]
    assert method == "GET"
    assert "/sheets/v3/spreadsheets/spreadsheet-token/sheets/query" in url
    assert kwargs["headers"]["Authorization"] == "Bearer tenant-token"


def test_read_values_uses_v2_values_endpoint():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    values = client.read_values("spreadsheet-token", "349176", "A1:I225")

    assert values == [["任务序号"]]
    assert "/sheets/v2/spreadsheets/spreadsheet-token/values/" in session.calls[-1][1]


def test_append_values_posts_values_payload():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    result = client.append_values("spreadsheet-token", "349176", "A:I", [["L36"]])

    assert result["updatedRange"] == "349176!A36:I36"
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert kwargs["json"]["valueRange"]["values"] == [["L36"]]


def test_update_values_puts_values_payload():
    session = FakeSession()
    client = FeishuSheetsClient("app", "secret", session=session)

    result = client.update_values("spreadsheet-token", "349176", "H36:I36", [["note", "link"]])

    assert result["updatedRange"] == "349176!H36:I36"
    assert session.calls[-1][0] == "PUT"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_feishu_sheets.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'digest.learn.sheets'`.

- [ ] **Step 3: Implement Sheets client**

Create `src/digest/learn/sheets.py`:

```python
import urllib.parse

import requests


class FeishuSheetsClient:
    def __init__(self, app_id: str, app_secret: str, session=requests):
        self.app_id = app_id
        self.app_secret = app_secret
        self.session = session

    def get_tenant_token(self) -> str:
        response = self.session.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"FEISHU_AUTH_{payload.get('code')}")
        return payload["tenant_access_token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_tenant_token()}"}

    @staticmethod
    def _check(payload: dict[str, object], prefix: str) -> dict[str, object]:
        if payload.get("code") != 0:
            raise RuntimeError(f"{prefix}_{payload.get('code')}")
        return payload.get("data", {})

    def get_sheets(self, spreadsheet_token: str) -> list[dict[str, object]]:
        response = self.session.get(
            f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = self._check(response.json(), "FEISHU_SHEETS_QUERY")
        return list(data.get("sheets", []))

    def read_values(self, spreadsheet_token: str, sheet_id: str, range_name: str) -> list[list[object]]:
        encoded_range = urllib.parse.quote(f"{sheet_id}!{range_name}", safe="")
        response = self.session.get(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{encoded_range}",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = self._check(response.json(), "FEISHU_SHEETS_READ")
        return list(data.get("valueRange", {}).get("values", []))

    def append_values(self, spreadsheet_token: str, sheet_id: str, range_name: str, values: list[list[object]]) -> dict[str, object]:
        encoded_range = urllib.parse.quote(f"{sheet_id}!{range_name}", safe="")
        response = self.session.post(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_append/{encoded_range}",
            headers=self._headers(),
            json={"valueRange": {"range": f"{sheet_id}!{range_name}", "values": values}},
            timeout=20,
        )
        response.raise_for_status()
        return self._check(response.json(), "FEISHU_SHEETS_APPEND")

    def update_values(self, spreadsheet_token: str, sheet_id: str, range_name: str, values: list[list[object]]) -> dict[str, object]:
        encoded_range = urllib.parse.quote(f"{sheet_id}!{range_name}", safe="")
        response = self.session.put(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{encoded_range}",
            headers=self._headers(),
            json={"valueRange": {"range": f"{sheet_id}!{range_name}", "values": values}},
            timeout=20,
        )
        response.raise_for_status()
        return self._check(response.json(), "FEISHU_SHEETS_UPDATE")
```

- [ ] **Step 4: Run tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_feishu_sheets.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/digest/learn/sheets.py tests/unit/test_feishu_sheets.py
git commit -m "feat(digest): add Feishu Sheets client"
```

---

### Task 4: Implement tracker validation, dedupe, and write planning

**Files:**
- Create: `src/digest/learn/tracker.py`
- Create: `tests/unit/test_learning_tracker.py`

**Interfaces:**
- Consumes:
  - `SHEET_HEADERS`
  - `LearningPlanCandidate`
  - `LearningPlanWritePlan`
  - `build_row(candidate, task_id, now)`
- Produces:
  - `validate_headers(values: list[list[object]]) -> None`
  - `next_task_id(values: list[list[object]]) -> str`
  - `find_duplicate(values: list[list[object]], candidate: LearningPlanCandidate) -> tuple[int, list[object]] | None`
  - `plan_learning_write(values, candidate, now) -> LearningPlanWritePlan`

- [ ] **Step 1: Write failing tracker tests**

Create `tests/unit/test_learning_tracker.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_tracker.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'digest.learn.tracker'`.

- [ ] **Step 3: Implement tracker**

Create `src/digest/learn/tracker.py`:

```python
import re
from datetime import datetime

from digest.learn.mapper import build_row
from digest.learn.models import SHEET_HEADERS, LearningPlanCandidate, LearningPlanWritePlan


def _cell(row: list[object], index: int) -> str:
    if len(row) <= index or row[index] is None:
        return ""
    value = row[index]
    if isinstance(value, list):
        return " ".join(str(part.get("link") or part.get("text") or "") if isinstance(part, dict) else str(part) for part in value)
    return str(value)


def validate_headers(values: list[list[object]]) -> None:
    if not values or tuple(str(value) for value in values[0][: len(SHEET_HEADERS)]) != SHEET_HEADERS:
        raise ValueError("LEARNING_PLAN_HEADER_MISMATCH")


def next_task_id(values: list[list[object]]) -> str:
    max_id = 0
    for row in values[1:]:
        match = re.fullmatch(r"L(\\d+)", _cell(row, 0).strip())
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


def plan_learning_write(values: list[list[object]], candidate: LearningPlanCandidate, now: datetime) -> LearningPlanWritePlan:
    validate_headers(values)
    duplicate = find_duplicate(values, candidate)
    if duplicate:
        row_number, row = duplicate
        task_id = _cell(row, 0)
        notes = _append_source_note(_cell(row, 7), candidate.source_date)
        link = _cell(row, 8) or candidate.url
        return LearningPlanWritePlan(
            action="update",
            range_name=f"H{row_number}:I{row_number}",
            values=[[notes, link]],
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
```

- [ ] **Step 4: Run tracker tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_learning_tracker.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/digest/learn/tracker.py tests/unit/test_learning_tracker.py
git commit -m "feat(digest): plan learning sheet writes"
```

---

### Task 5: Add learning-plan CLI preview/apply flow

**Files:**
- Create: `src/digest/jobs/learning_plan.py`
- Modify: `src/digest/config.py`
- Modify: `src/digest/models.py`
- Create: `tests/integration/test_learning_plan_cli.py`

**Interfaces:**
- Consumes:
  - `load_config(root: Path) -> AppConfig`
  - `FeishuSheetsClient`
  - `plan_learning_write`
- Produces:
  - CLI command:
    - Preview: `python -m digest.jobs.learning_plan --title ... --summary ... --url ... --source-date ... --intent ...`
    - Apply: same command with `--apply`

- [ ] **Step 1: Write failing CLI test**

Create `tests/integration/test_learning_plan_cli.py`:

```python
import json

from digest.jobs import learning_plan


class FakeSheets:
    def get_sheets(self, spreadsheet_token):
        return [{"sheet_id": "349176", "title": "主任务"}]

    def read_values(self, spreadsheet_token, sheet_id, range_name):
        return [
            ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"],
            ["L35", "大模型", "Existing", "", "待开始", "", "中", "", ""],
        ]

    def append_values(self, spreadsheet_token, sheet_id, range_name, values):
        return {"updatedRange": "349176!A36:I36"}

    def update_values(self, spreadsheet_token, sheet_id, range_name, values):
        return {"updatedRange": range_name}


def test_preview_does_not_write(monkeypatch, capsys):
    monkeypatch.setattr(learning_plan, "build_sheets_client", lambda config: FakeSheets())

    exit_code = learning_plan.main([
        "--title", "Graphify",
        "--summary", "将代码和文档转为知识图谱。",
        "--url", "https://github.com/safishamsi/graphify",
        "--source-date", "2026-06-29",
        "--intent", "感兴趣",
        "--now", "2026-06-29T10:00:00+08:00",
    ])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "preview"
    assert output["plan"]["action"] == "append"
    assert output["plan"]["values"][0][0] == "L36"


def test_apply_appends(monkeypatch, capsys):
    monkeypatch.setattr(learning_plan, "build_sheets_client", lambda config: FakeSheets())

    exit_code = learning_plan.main([
        "--title", "Graphify",
        "--summary", "将代码和文档转为知识图谱。",
        "--url", "https://github.com/safishamsi/graphify",
        "--source-date", "2026-06-29",
        "--intent", "感兴趣",
        "--now", "2026-06-29T10:00:00+08:00",
        "--apply",
    ])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "apply"
    assert output["result"]["updatedRange"] == "349176!A36:I36"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/integration/test_learning_plan_cli.py -q
```

Expected: FAIL because `digest.jobs.learning_plan` does not exist.

- [ ] **Step 3: Add optional config fields**

Modify `src/digest/models.py` by extending `AppConfig` at the end:

```python
    learning_plan_spreadsheet_token: str = "R4LAsRmQKhfMXYtV7UacSeaGngg"
    learning_plan_sheet_title: str = "主任务"
```

Modify `src/digest/config.py` before returning `AppConfig`:

```python
    learning_plan_spreadsheet_token = os.environ.get(
        "DAILY_AI_DIGEST_LEARNING_PLAN_SPREADSHEET_TOKEN",
        "R4LAsRmQKhfMXYtV7UacSeaGngg",
    )
    learning_plan_sheet_title = os.environ.get(
        "DAILY_AI_DIGEST_LEARNING_PLAN_SHEET_TITLE",
        "主任务",
    )
```

Then pass those two fields into `AppConfig(...)` after `feishu_chat_id`.

- [ ] **Step 4: Implement CLI**

Create `src/digest/jobs/learning_plan.py`:

```python
import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.config import load_config
from digest.learn.models import LearningPlanCandidate
from digest.learn.sheets import FeishuSheetsClient
from digest.learn.tracker import plan_learning_write


def build_sheets_client(config):
    return FeishuSheetsClient(config.feishu_app_id, config.feishu_app_secret)


def _resolve_sheet_id(sheets: list[dict[str, object]], title: str) -> str:
    for sheet in sheets:
        if sheet.get("title") == title:
            return str(sheet["sheet_id"])
    raise ValueError("LEARNING_PLAN_SHEET_NOT_FOUND")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a Daily AI Digest interest into Feishu learning plan")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-date", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--section", default="生产力项目")
    parser.add_argument("--stars", type=int)
    parser.add_argument("--now")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[3]
    config = load_config(root)
    client = build_sheets_client(config)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo(config.schedule.get("timezone", "Asia/Shanghai")))
    candidate = LearningPlanCandidate(
        source_date=args.source_date,
        title=args.title,
        summary=args.summary,
        url=args.url,
        section=args.section,
        stars=args.stars,
        user_intent=args.intent,
    )

    sheet_id = _resolve_sheet_id(
        client.get_sheets(config.learning_plan_spreadsheet_token),
        config.learning_plan_sheet_title,
    )
    values = client.read_values(config.learning_plan_spreadsheet_token, sheet_id, "A1:I225")
    plan = plan_learning_write(values, candidate, now)
    payload = {"mode": "apply" if args.apply else "preview", "sheet_id": sheet_id, "plan": asdict(plan)}

    if args.apply:
        if plan.action == "append":
            result = client.append_values(config.learning_plan_spreadsheet_token, sheet_id, plan.range_name, plan.values)
        elif plan.action == "update":
            result = client.update_values(config.learning_plan_spreadsheet_token, sheet_id, plan.range_name, plan.values)
        else:
            raise ValueError(f"unknown action: {plan.action}")
        payload["result"] = result

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/integration/test_learning_plan_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run config tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_config.py tests/integration/test_learning_plan_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/digest/jobs/learning_plan.py src/digest/config.py src/digest/models.py tests/integration/test_learning_plan_cli.py
git commit -m "feat(digest): add learning plan tracking CLI"
```

---

### Task 6: Add operations documentation and safe real-read verification

**Files:**
- Modify: `docs/operations.md`
- Test: `scripts/validate_config.sh` if config behavior changes

**Interfaces:**
- Produces documented commands:
  - Preview command
  - Apply command
  - Real read-only verification command

- [ ] **Step 1: Update operations docs**

Append to `docs/operations.md`:

````markdown
## Learning plan tracking

The learning-plan tracker records user-selected Daily AI Digest items into the Feishu spreadsheet `学习计划追踪 2026`, sheet `主任务`.

Preview only:

```bash
PYTHONPATH=src .venv/bin/python -m digest.jobs.learning_plan \
  --title "Graphify" \
  --summary "将代码和文档转为知识图谱。" \
  --url "https://github.com/safishamsi/graphify" \
  --source-date "2026-06-29" \
  --intent "感兴趣" \
  --stars 5154
```

Apply after user confirmation:

```bash
PYTHONPATH=src .venv/bin/python -m digest.jobs.learning_plan \
  --title "Graphify" \
  --summary "将代码和文档转为知识图谱。" \
  --url "https://github.com/safishamsi/graphify" \
  --source-date "2026-06-29" \
  --intent "感兴趣" \
  --stars 5154 \
  --apply
```

Rules:

- Never apply without explicit user confirmation.
- Do not record every digest item automatically.
- The tracker writes only columns A-I.
- Duplicate rows update notes/link only.
- Real write smoke tests require user approval.
````

- [ ] **Step 2: Run docs grep check**

Run:

```bash
rg -n "Learning plan tracking|--apply|A-I|explicit user confirmation" docs/operations.md
```

Expected: all terms appear.

- [ ] **Step 3: Run all tests and config validation**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
scripts/validate_config.sh
```

Expected:

```text
... passed
config: valid
```

- [ ] **Step 4: Commit**

```bash
git add docs/operations.md
git commit -m "docs(digest): document learning plan tracking"
```

---

### Task 7: User-approved real Feishu smoke test

**Files:**
- No code files unless a bug is found.

**Interfaces:**
- Consumes:
  - `digest.jobs.learning_plan`
- Produces:
  - One read-only verification result.
  - Optionally one user-approved append/update result.

- [ ] **Step 1: Perform read-only preview against real Feishu**

Run:

```bash
set -a
[ -f /opt/personal-agent-workspace/.env ] && . /opt/personal-agent-workspace/.env
[ -f /root/.claude-to-im/config.env ] && . /root/.claude-to-im/config.env
set +a
PYTHONPATH=src .venv/bin/python -m digest.jobs.learning_plan \
  --title "Graphify" \
  --summary "将代码和文档转为知识图谱。" \
  --url "https://github.com/safishamsi/graphify" \
  --source-date "2026-06-29" \
  --intent "感兴趣" \
  --stars 5154
```

Expected: JSON with `"mode": "preview"` and either `"action": "append"` or `"action": "update"`. No spreadsheet write occurs.

- [ ] **Step 2: Ask user before write**

Show the planned write message from JSON, for example:

```text
准备记录：L36｜Agentic Coding｜Graphify 项目学习｜优先级：中｜状态：待开始。确认写入？
```

Stop until the user confirms.

- [ ] **Step 3: Apply only after confirmation**

Run the same command with `--apply`.

Expected: JSON with `"mode": "apply"` and Feishu `updatedRange`.

- [ ] **Step 4: Verify real sheet state**

Run preview again with the same candidate.

Expected: the plan changes to duplicate update mode, proving the written row is now detectable.

- [ ] **Step 5: Commit only if a bug fix was needed**

If no code changed, do not commit.

If a bug was fixed:

```bash
git add src/digest/learn src/digest/jobs/learning_plan.py tests
git commit -m "fix(digest): harden learning plan Feishu write"
```

---

## Self-Review

- Spec coverage: This plan covers MCP-style Feishu Sheets access, header validation, L-number generation, duplicate detection, append/update rules, confirmation flow, security boundaries, and real smoke-test gating.
- Placeholder scan: No unfinished placeholder markers are present.
- Type consistency: `LearningPlanCandidate`, `LearningPlanRow`, `LearningPlanWritePlan`, `FeishuSheetsClient`, and `plan_learning_write` are introduced before downstream tasks consume them.
- Scope check: The plan intentionally does not modify daily digest auto-delivery or create child sheets; those remain non-goals from the spec.
