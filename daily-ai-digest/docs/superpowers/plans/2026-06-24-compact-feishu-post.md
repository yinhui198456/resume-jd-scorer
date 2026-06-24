# Compact Feishu Post Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a single compact Feishu rich-text Post containing at most 8 top stories and 3 candidates, with complete top-story summaries capped at 100 characters and one primary link per item.

**Architecture:** Keep the persisted Markdown digest and runtime checkpoints unchanged, but add a display-specific Post renderer. Replace broad topic-overlap clustering with conservative normalized-title grouping, then route normal digests through `send_post()` while retaining plain-text fault delivery.

**Tech Stack:** Python 3.12, pytest, requests, Feishu `im/v1/messages`, YAML configuration.

## Global Constraints

- Use the existing `Codex-学习助理` credentials from `~/.claude-to-im/config.env`.
- Send one Feishu message per successful run; do not introduce CardKit.
- Limit visible content to 8 top stories and 3 candidates.
- Limit each visible top-story summary to 100 Unicode characters, including an ellipsis, while prioritizing a complete explanation.
- Show no run ID, empty section, `why_it_matters`, raw URL, or secondary source link in the Post.
- Preserve all historical files under `data/`.
- Do not send a real Feishu message until automated tests pass and the user explicitly approves a smoke test.

---

### Task 1: Conservative clustering and 8+3 selection

**Files:**
- Modify: `src/digest/cluster/group.py`
- Modify: `configs/filters.yml`
- Modify: `tests/unit/test_cluster.py`
- Modify: `tests/integration/test_daily.py`

**Interfaces:**
- Consumes: `cluster_items(items: list[NewsItem]) -> list[list[NewsItem]]`.
- Produces: clusters containing only case-folded, whitespace-normalized equal titles; configuration quotas `top_stories=8` and `candidates=3`.

- [ ] **Step 1: Write failing clustering and quota tests**

```python
def test_shared_topic_does_not_merge_unrelated_titles():
    first = item("https://example.com/1")
    second = item("https://example.com/2")
    first.normalized_title = "Codex release"
    second.normalized_title = "AI governance report"
    first.topic_tags = second.topic_tags = ["Agent"]
    assert len(cluster_items([first, second])) == 2


def test_equal_normalized_titles_cluster():
    first = item("https://example.com/1")
    second = item("https://example.com/2")
    first.normalized_title = " Codex   Release "
    second.normalized_title = "codex release"
    first.topic_tags = ["Codex"]
    second.topic_tags = ["Agent"]
    assert len(cluster_items([first, second])) == 1
```

Update the integration fixture configuration to:

```python
"quotas": {"top_stories": 8, "candidates": 3}
```

and assert:

```python
assert report.item_count == 11
assert Counter(item["section"] for item in generated) == {
    "重点资讯": 8,
    "候选池": 3,
}
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/unit/test_cluster.py tests/integration/test_daily.py
```

Expected: the unrelated-title test reports one cluster instead of two, and the quota test reports 20 items instead of 11.

- [ ] **Step 3: Implement conservative title grouping and configuration**

Replace topic-overlap grouping with:

```python
def _title_key(item: NewsItem) -> str:
    return " ".join(item.normalized_title.casefold().split())


def cluster_items(items: list[NewsItem]) -> list[list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = {}
    for item in items:
        groups.setdefault(_title_key(item), []).append(item)
    clusters = list(groups.values())
    for cluster in clusters:
        cluster_id = hashlib.sha256(
            "\0".join(sorted(item.news_id for item in cluster)).encode()
        ).hexdigest()
        for item in cluster:
            item.cluster_id = cluster_id
    return clusters
```

Set:

```yaml
quotas:
  top_stories: 8
  candidates: 3
```

Retain the other quota keys for future section routing.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all focused tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add daily-ai-digest/src/digest/cluster/group.py daily-ai-digest/configs/filters.yml daily-ai-digest/tests/unit/test_cluster.py daily-ai-digest/tests/integration/test_daily.py
git commit -m "fix(digest): enforce compact selection quotas"
```

---

### Task 2: Build a compact Feishu Post payload

**Files:**
- Modify: `src/digest/generate/render.py`
- Modify: `tests/unit/test_render.py`

**Interfaces:**
- Produces: `compact_text(text: str, limit: int = 100) -> str`.
- Produces: `render_feishu_post(generated_at: str, sections: dict[str, list[DigestItem]], source_health: dict[str, object]) -> dict[str, object]`.

- [ ] **Step 1: Write failing renderer tests**

```python
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
    assert "无" not in serialized
```

- [ ] **Step 2: Run renderer tests and verify RED**

```bash
.venv/bin/python -m pytest -q tests/unit/test_render.py
```

Expected: import errors for `compact_text` and `render_feishu_post`.

- [ ] **Step 3: Implement compact text and Post rendering**

Add:

```python
from datetime import datetime


def compact_text(text: str, limit: int = 100) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def _link_line(label: str, url: str) -> list[dict[str, str]]:
    elements: list[dict[str, str]] = [{"tag": "text", "text": label}]
    if url:
        elements.append({"tag": "a", "text": "查看原文", "href": url})
    return elements


def render_feishu_post(generated_at, sections, source_health):
    timestamp = datetime.fromisoformat(generated_at)
    top = sections.get("重点资讯", [])[:8]
    candidates = sections.get("候选池", [])[:3]
    health = "来源正常" if source_health.get("status") == "healthy" else "部分来源异常"
    content = [[{"tag": "text", "text": f"{health} · {len(top)} 条重点 · {len(candidates)} 条候选"}]]
    for index, item in enumerate(top, 1):
        content.append([{"tag": "text", "text": f"{index}. {item.chinese_title}", "style": ["bold"]}])
        content.append([{"tag": "text", "text": compact_text(item.summary)}])
        content.append(_link_line("", item.source_links[0] if item.source_links else ""))
    if candidates:
        content.append([{"tag": "text", "text": "候选速览", "style": ["bold"]}])
        for item in candidates:
            content.append(_link_line(f"• {item.chinese_title}  ", item.source_links[0] if item.source_links else ""))
    return {"zh_cn": {"title": f"每日 AI 资讯｜{timestamp.month}月{timestamp.day}日", "content": content}}
```

- [ ] **Step 4: Run renderer tests and verify GREEN**

Run the Step 2 command. Expected: all renderer tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add daily-ai-digest/src/digest/generate/render.py daily-ai-digest/tests/unit/test_render.py
git commit -m "feat(digest): render compact Feishu post"
```

---

### Task 3: Add Feishu Post delivery

**Files:**
- Modify: `src/digest/deliver/feishu.py`
- Modify: `tests/unit/test_feishu.py`

**Interfaces:**
- Produces: `FeishuDelivery.send_post(payload: dict[str, object], delivery_key: str) -> DeliveryResult`.
- Preserves: `send_text(text: str, delivery_key: str) -> DeliveryResult` for fault digests and smoke diagnostics.

- [ ] **Step 1: Write the failing delivery test**

```python
def test_send_post_targets_chat_with_post_payload():
    session = FakeSession()
    session.queue({"code": 0, "tenant_access_token": "token", "expire": 7200})
    session.queue({"code": 0, "data": {"message_id": "om_post"}})
    delivery = FeishuDelivery("cli_test", "secret", "oc_test", session)
    payload = {"zh_cn": {"title": "每日 AI 资讯", "content": []}}

    result = delivery.send_post(payload, "run-1:sha")

    _, request = session.requests[-1]
    assert request["json"]["receive_id"] == "oc_test"
    assert request["json"]["msg_type"] == "post"
    assert json.loads(request["json"]["content"]) == payload
    assert result.message_id == "om_post"
```

- [ ] **Step 2: Run the delivery test and verify RED**

```bash
.venv/bin/python -m pytest -q tests/unit/test_feishu.py
```

Expected: `AttributeError` because `send_post` does not exist.

- [ ] **Step 3: Implement `send_post` without changing authentication**

```python
def send_post(self, payload: dict[str, object], delivery_key: str) -> DeliveryResult:
    return self._send("post", payload, delivery_key)


def _send(self, msg_type: str, content: object, delivery_key: str) -> DeliveryResult:
    token = self.get_tenant_token()
    response = self.session.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": self.chat_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        },
        timeout=20,
    )
    response.raise_for_status()
    response_payload = response.json()
    if response_payload.get("code") != 0:
        raise RuntimeError(f"FEISHU_SEND_{response_payload.get('code')}")
    return DeliveryResult(delivery_key, response_payload["data"]["message_id"], "succeeded")
```

Refactor `send_text` to call `_send("text", {"text": text}, delivery_key)`.

- [ ] **Step 4: Run delivery tests and verify GREEN**

Run the Step 2 command. Expected: all delivery tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add daily-ai-digest/src/digest/deliver/feishu.py daily-ai-digest/tests/unit/test_feishu.py
git commit -m "feat(digest): deliver Feishu rich-text posts"
```

---

### Task 4: Wire compact Post delivery into the daily job

**Files:**
- Modify: `src/digest/jobs/daily.py`
- Modify: `src/digest/generate/minimax.py`
- Modify: `tests/integration/test_daily.py`
- Modify: `tests/unit/test_minimax.py`
- Modify: `docs/operations.md`

**Interfaces:**
- Consumes: `render_feishu_post(...)` and `FeishuDelivery.send_post(...)`.
- Preserves: Markdown persistence before delivery and plain-text total-failure delivery.

- [ ] **Step 1: Write failing integration and prompt tests**

Extend `FakeDelivery` with separate counters and payload capture:

```python
def send_post(self, payload, delivery_key):
    self.post_count += 1
    self.last_post = payload
    return Result()
```

Assert a successful run uses Post and only the representative URL:

```python
assert delivery.post_count == 1
assert delivery.text_count == 0
assert "why_it_matters" not in json.dumps(delivery.last_post)
assert generated[0]["source_links"] == ["https://example.com/release"]
```

Assert total failure uses text:

```python
assert delivery.text_count == 1
assert delivery.post_count == 0
```

Assert the MiniMax system prompt contains `100`, `complete`, and `characters`.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
.venv/bin/python -m pytest -q tests/integration/test_daily.py tests/unit/test_minimax.py
```

Expected: successful runs still call `send_text`, source links contain the full cluster, and the prompt lacks the complete 100-character instruction.

- [ ] **Step 3: Implement job routing and prompt control**

In `daily.py`:

```python
from digest.generate.render import render_digest, render_fault_digest, render_feishu_post
```

When constructing each `DigestItem`, set:

```python
source_links=[primary.canonical_url] if primary.canonical_url else []
```

For normal output, build:

```python
post_payload = render_feishu_post(now.isoformat(), sections, health)
delivery_mode = "post"
```

For fault output, set `post_payload = None` and `delivery_mode = "text"`. At delivery:

```python
if delivery_mode == "post":
    result = dependencies.delivery.send_post(post_payload, delivery_key)
else:
    result = dependencies.delivery.send_text(text, delivery_key)
```

In `minimax.py`, extend the system prompt with:

```text
Write one complete, explanatory summary within 100 Chinese characters. Return exactly one JSON object...
```

Update `docs/operations.md` to describe normal Post delivery and plain-text fault delivery.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all focused tests pass.

- [ ] **Step 5: Run full verification**

```bash
.venv/bin/python -m pytest -q
scripts/validate_config.sh
systemd-analyze verify deploy/daily-ai-digest.service deploy/daily-ai-digest.timer
git diff --check -- daily-ai-digest
```

Expected: all tests and configuration checks pass. The only acceptable systemd warning is the pre-existing unrelated `tat_agent.service` `/var/run` warning.

- [ ] **Step 6: Inspect a non-delivering rendered payload**

Run an integration fixture with fake delivery and print only counts:

```text
top=8 candidates=3 max_summary_chars=100 post_messages=1 text_messages=0
```

Expected: no network delivery occurs and every limit matches the specification.

- [ ] **Step 7: Commit Task 4**

```bash
git add daily-ai-digest/src/digest/jobs/daily.py daily-ai-digest/src/digest/generate/minimax.py daily-ai-digest/tests/integration/test_daily.py daily-ai-digest/tests/unit/test_minimax.py daily-ai-digest/docs/operations.md
git commit -m "feat(digest): send compact daily Feishu post"
```

---

### Task 5: Controlled Feishu smoke test

**Files:**
- Read: `data/state/delivery_log.json`
- Read: `data/state/run_state.json`

**Interfaces:**
- Consumes: the verified compact Post path.
- Produces: one user-approved real message ID in the current Feishu group.

- [ ] **Step 1: Obtain explicit user approval for one real Post message**

Do not infer approval from implementation approval.

- [ ] **Step 2: Send one compact Post smoke message**

Use the existing `Codex-学习助理` application and current group target. Do not run a second full digest unless the user requests it.

- [ ] **Step 3: Verify the returned message ID and ask the user to confirm visual acceptance**

Expected: Feishu returns code 0 and a non-empty `om_...` message ID.

- [ ] **Step 4: Enable the timer only after separate user approval**

Timer installation and enablement remain outside this implementation plan's automatic actions.
