# quiz_bot.py 修复记录 — 2026-06-08

## 背景

2026-06-08 刷题约 3 小时后，用户要求暂停并做系统性诊断。用 2 个 subagent 分别验证后确认 4 个 bug，全部修复。

## 修复清单

### Fix 1：`cmd_answer` 不记录 `result` 字段（P0）

**位置**：`quiz_bot.py` 第 377 行后

**修复前**：
```python
t['status'] = status
# result 变量在第 367/372 行计算了，但从未写入顶层
```

**修复后**：
```python
t['status'] = status
t['result'] = result  # P0 fix: 写入答题结果到顶层
```

**影响**：之前 284 条 tracking 记录均无顶层 result，无法统计正确率。

---

### Fix 2：开放题无限循环（P0）

**位置**：`cmd_next()` 函数，第 155 行新增常量，第 174-181 行新增检测逻辑

**修复**：
```python
OPEN_QUESTION_PATTERNS = ['面试建议', '回忆题', '开放性', '说说你', '你的看法']
# 在已学习检查之后、质量门控检查之前：
is_open = any(pat in q_text for pat in OPEN_QUESTION_PATTERNS) or \
          any(pat in opt for opt in options for pat in OPEN_QUESTION_PATTERNS)
if is_open:
    skipped_count += 1
    continue
```

**触发场景**：Q-M01_LLM基础67（"最近半年印象最深的 Agent 论文/项目？"）选项 A 是"面试建议"，非 MCQ 格式。用户无法作答 → 无 tracking → 每次 next 都重新找到。

---

### Fix 3：`modules_progress.topics_done` 不递增（P1）

**位置**：`quiz_bot.py` 第 405 行

**修复前**：
```python
if is_correct:
    mp['topics_done'] = mp.get('topics_done', 0)  # 赋值给自己，永远不+1
```

**修复后**：
```python
if is_correct:
    mp['topics_done'] = mp.get('topics_done', 0) + 1  # P1 fix: 答对才+1
```

**影响**：刷题 3 小时，所有模块的 topics_done 都停留在初始值。

---

### Fix 4：P4 hash 校验过严导致误拦截（P1）

**位置**：`quiz_bot.py` 第 304-347 行

**根因**：`quiz_bot_state.json` 是单例文件，每次 `next` 都会覆盖。用户跳题后返回答题，state hash 是后一题的，与当前题不匹配 → 拦截。

**修复逻辑**：
- `quiz_hash_log.jsonl` 是**不可变追加写入**，作为权威源
- `state hash` 单独不匹配时，如果 log hash 匹配 → **放行**
- 只有 `log hash` 不匹配 或 `快照` 不匹配（且无 log 背书）→ **拒绝**

```python
# 拒绝条件：log 不匹配 或 快照不匹配（state hash 单独不匹配时，如果有 log 背书则放行）
if log_mismatch or (snapshot_mismatch and not log_hash):
    # 拒绝判题
```

## 验证方式

Subagent 独立验证：
1. ✅ 读取代码确认 4 处修复在正确行号
2. ✅ `next` 不再卡住 Q-M01_LLM基础67
3. ✅ `next M01_LLM基础` 正确跳过开放题
4. ✅ answer 后 tracking 写入 result: 'pass'
5. ✅ topics_done 答对后正确 +1
