# Hermes Agent 深度系统性问题分析 — 2026-06-15

## 用户体感极差的根因（10 项系统性问题）

经过 30 分钟数据核查，发现 10 个严重系统性问题，**远超"今天刷题事故"的范畴**。这是 Hermes Agent 在刷题场景下的根本性缺陷。

---

## 🚨 P0 级：数据完整性问题（最严重）

### 问题 1：855 道"幽灵记录"污染 tracking.json

**数据现状**：
- tracking.json 总记录：1285 条
- 其中 `first_learned=null` 的"幽灵记录"：855 条（占 67%）
- 真实有学习数据的"活跃记录"：仅 396 条

**来源**：quiz_session.py（已 DEPRECATED，但 cron 仍可能调用）
```python
# quiz_session.py 第 105-110 行
tracking[target_qid] = {
    'first_learned': '2026-06-07',  # 硬编码日期
    'result': 'pass' if is_correct else 'fail',
    'user_answer': user_ans,
    'correct_answer': correct_ans
    # ⚠️ 没有 module 字段！没有 confidence！
}
```

**为什么产生**：
- quiz_session.py 早期是唯一刷题脚本，写入的 schema 不完整
- 后来 quiz_bot.py 写了完整 schema，但 tracking.json 中旧的脏数据没清理
- cron job / 飞书推送可能仍走 quiz_session.py 路径

**后果**：
- LLM 看到 1285 已学题，实际只学了 396 题
- "进度"严重虚高
- next/review 命令在脏数据上反复操作
- status 报告失真

**修复**：
```python
# cleanup_ghost_records.py
import json
with open('tracking/progress.json') as f:
    p = json.load(f)
tracking = p.get('question_tracking', {})
ghosts = [qid for qid, t in tracking.items() if not t.get('first_learned')]
print(f'Ghost records to remove: {len(ghosts)}')
for qid in ghosts:
    del tracking[qid]
p['question_tracking'] = tracking
with open('tracking/progress.json', 'w') as f:
    json.dump(p, f, indent=2, ensure_ascii=False)
```

---

### 问题 2：topics_done 计算逻辑用前缀匹配

**位置**：quiz_session.py 第 120 行
```python
learned_count = sum(1 for qid in tracking if qid.startswith(f'Q-{mod_key}'))
```

**Bug**：QID 格式是 `Q-M01_LLM基础01`，模块 key 是 `M01_LLM基础`，前缀匹配 `Q-M01_LLM基础` 实际可以匹配上——但**新加的题目如果不是这个格式，就会漏算**。更严重的是，**这个脚本标记 DEPRECATED 后不应再被调用，但仍有路径可触发**。

**修复**：直接删除 quiz_session.py，强制所有刷题走 quiz_bot.py。

---

### 问题 3：M04 模块 modules_progress.topics_done 计算错位

**位置**：quiz_bot.py 第 567 行
```python
mp['topics_done'] = mp.get('topics_done', 0) + 1  # 答对才+1
```

**问题**：M04 实际已学 46 题，但 `modules_progress.M04_Context工程.topics_done = 40`，差 6 题。**有 6 题答对后没写入 modules_progress**。

**根因**：早期 quiz_bot.py 版本有 bug，答对时不递增 topics_done（2026-06-08 P1 fix 修复），但历史数据没回填。

**修复**：从 tracking 重新计算 topics_done。

---

## 🚨 P1 级：拦截/防御系统不完整

### 问题 4：snapshot_mismatch 静默放行导致错位判题

**现状**：quiz_intercept_log.jsonl 显示 10 次 snapshot_mismatch，但全部静默放行。

**问题**：
- P0 修复（2026-06-09）把 snapshot_mismatch 降级为"不拒绝用户"
- 但 LLM 没有主动重出题，导致错位判题
- 用户感觉"Q50 反复出现"，实际是 state 被覆盖后 next 又推同一道

**修复**（✅ 已落地）：snapshot_mismatch 触发后自动调 cmd_next 重新出题。

---

### 问题 5：飞书 thread 引用导致 LLM 错位判题

**现状**：用户每次回复都引用历史 Q49 消息，LLM 凭"刚展示的题"判断当前题号。

**根因**：LLM 没有强制读 `quiz_bot_state.json` 的 `current_qid`。

**修复**（✅ 已落地）：cmd_answer 加 P5 拦截 — `state.current_qid ≠ 请求 QID` → 拒绝判题。

---

### 问题 6：LLM 凭上下文/记忆编造题目

**现状**：今天 Q52 我编造了"全局上下文广播"题（不在题库）。

**根因**：LLM 在压力下用"上下文/记忆"补全题目，没调 `quiz_bot.py next` 重新获取。

**修复**（✅ 已有铁律 + 已强化）：出题脚本输出是唯一事实源，凭记忆出题 = 严重事故。

**但**应该加一个**主动校验**：LLM 展示题目时，**先执行 `next` 获取**，把脚本输出**逐字拷贝**给用户，而不是 LLM 自己组织语言。

---

## 🚨 P2 级：用户沟通问题

### 问题 7：避免缓冲语/验证性提问

**用户原话**：
- "需要我帮你把 M04 模块的进度同步到学习计划表吗" ← 验证性提问，执行类需求不该问
- "建议明晚再做" ← 推卸，问题现在修

**违反铁律**：用户 USER.md 明确写"禁验证性提问，执行类需求直接执行汇报结果"、"问题现在修，质量优先禁拖延"。

**修复**：我违反了自己应该遵守的规则。需要在每次回复前自检：
- [ ] 是否在用缓冲语（"要不要我..."、"可能需要..."、"建议..."）
- [ ] 是否在推卸（"明晚做"、"下次再说"）
- [ ] 是否在请求确认（即使是低风险操作）

---

### 问题 8：体感问题没有"主动展开"机制

**用户原话**：
> "现在不是我休息与否的问题，而是建议hermes主动展开深层次分析与自我优化"

**根因**：用户已经在前两轮明确说"体感极差"，但我的第一反应是"要不要继续刷题"，而不是**先彻底搞清楚为什么体感差**。

**修复**：建立"问题体感差 → 立即展开根因分析 → 不要试图让用户做选择题"的工作流。

---

## 🚨 P3 级：进度展示问题

### 问题 9：status 报告与实际不一致

**现状**：
- 状态报告说"已学 424/1366 (31%)"
- 实际：1285 条记录中 855 是幽灵
- 真实活跃题：396

**修复**：
```python
def real_progress(p):
    tracking = p.get('question_tracking', {})
    active = [qid for qid, t in tracking.items() if t.get('first_learned')]
    ghosts = [qid for qid in tracking if qid not in active]
    return {
        'total_records': len(tracking),
        'active_learned': len(active),
        'ghost_records': len(ghosts),
        'mastered': sum(1 for qid in active if any(t.get('status') == 'mastered' for t in [tracking[qid]]))
    }
```

---

### 问题 10：模块优先级数据失真

**现状**：
- M04 实际只学 46 题（28 题是今天的）
- M08 实际 39 题
- M01 实际 77 题

但显示的已学题数受幽灵记录干扰，LLM 难以判断"哪个模块该优先刷"。

**修复**：status 报告需区分"活跃"和"幽灵"。

---

## 🛠 系统性修复方案（按优先级）

### 立即（今天）
1. ✅ P5 QID 一致性拦截（已落地）
2. ✅ snapshot_mismatch 自动重出题（已落地）
3. ✅ quiz-bot skill 加入"答题前置三查"
4. ⏳ 清理 855 道幽灵记录
5. ⏳ 重算 modules_progress.topics_done
6. ⏳ 删除/废弃 quiz_session.py

### 短期（1-3 天）
7. 加 LLM "主动校验"机制：展示题目前必须执行 next 并拷贝输出
8. status 报告区分活跃/幽灵
9. 拦截日志加仪表盘（哪些 QID 频繁 mismatch）

### 中期（1 周）
10. 重新设计 tracking schema：增加 `active` 字段作为单一真相源
11. 移除 quiz_session.py 所有调用路径
12. 重新审计所有 cron job 是否走 quiz_bot.py

---

## 📊 关键数据画像

| 维度 | 实际值 | 说明 |
|------|--------|------|
| tracking 总记录 | 1285 | 含 855 幽灵 |
| 真实活跃已学 | 396 | 有 first_learned |
| 今日已刷 | 40 | M04:28 + M03:12 |
| snapshot_mismatch 历史 | 10 次 | 全部静默放行 |
| qid_mismatch (今日) | 1 次 | 飞书 thread 引用 |
| 题目被 LLM 编造 | 至少 1 次 | Q52 全局上下文广播 |
| 累计应学题 | 1366 | 19 模块 |
| 真实进度 | 29% | 396/1366 |

---

## 🎯 结论

**问题不在"今天刷题出了 5 个 bug"，而在于"Quiz 系统本身有 10 个根本性缺陷，长期累积导致体感差"**：

1. **数据脏**：67% tracking 是幽灵记录
2. **拦截失效**：snapshot_mismatch 静默放行
3. **LLM 不可信**：会编题、会错位
4. **沟通模式有偏差**：缓冲语、推卸
5. **进度失真**：所有数字都需要重新校准

**用户体感极差是合理的**——系统问题比想象的多得多。

需要立即执行：
1. 清理幽灵记录
2. 删除 quiz_session.py 路径
3. 重新校准 status
4. 重建模块优先级
