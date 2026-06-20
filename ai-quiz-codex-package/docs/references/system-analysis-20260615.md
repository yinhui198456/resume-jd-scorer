# Quiz System 深度问题分析 — 2026-06-15

## 背景

用户在 M04 Context工程 模块连续刷题后，反馈"体感极差"。**30 分钟数据核查发现 10 个系统性问题，远超单次会话 bug 范畴**。本文件记录所有问题的根因、数据画像、修复方案。

---

## 📊 关键数据画像

| 维度 | 显示值 | 实际值 | 误差 |
|------|--------|--------|------|
| tracking 总记录 | 1285 | 1285 | 0 |
| **真实活跃已学** | 424 (32%) | **427 (31.3%)** | -3（已修复）|
| 幽灵记录 | 0（未识别）| 855 | 855（已修复）|
| M04 topics_done | 40 | 52 | -12（已修复）|
| 今日已刷 | 40 | 40 | 0 |
| 总应学题 | 1366 | 1366 | 0 |

**核心发现**：68% tracking 记录是 `first_learned=null` 的幽灵（来源 quiz_session.py）。

---

## 🚨 P0 级问题（数据完整性）

### P0-1：855 道"幽灵记录"污染 tracking.json

**症状**：status 报告显示"已学 1285/1366 (94%)"，接近完成；实际只学 396 题 (29%)。

**根因**：quiz_session.py（已标记 DEPRECATED 但仍可调用）写入的 tracking 记录 schema 不完整：

```python
# quiz_session.py cmd_answer 第 105-110 行
tracking[target_qid] = {
    'first_learned': '2026-06-07',  # 硬编码日期
    'result': 'pass' if is_correct else 'fail',
    'user_answer': user_ans,
    'correct_answer': correct_ans
    # ⚠️ 没有 module 字段！
    # ⚠️ 没有 confidence 字段！
    # ⚠️ 没有 review_count 字段！
}
```

**修复**：使用 `scripts/cleanup_ghost_records.py` 清理。已在本 session 修复（855 → 0）。

### P0-2：M04 topics_done 错位

**症状**：M04 实际答对 52 题，但 `modules_progress.M04_Context工程.topics_done = 40`。

**根因**：2026-06-08 之前 quiz_bot.py 有 bug — 答对时不递增 topics_done。修复后历史数据未回填。

**修复**：cleanup 脚本的 Step 3 已重算所有模块 topics_done。

### P0-3：quiz_session.py 仍可执行

**症状**：脚本顶部标记 DEPRECATED，但权限未撤销（`chmod +x`），cron job 仍可能调用。

**修复**：`chmod -x scripts/quiz_session.py`（已执行）。

---

## 🚨 P1 级问题（拦截/防御不完整）

### P1-1：snapshot_mismatch 静默放行导致错位判题

**症状**：`quiz_intercept_log.jsonl` 显示 10 次 snapshot_mismatch，全部静默放行；用户感觉"Q50 反复出现"。

**根因**：2026-06-09 P0 修复把 snapshot_mismatch 降级为"不拒绝用户"，但 LLM 没有主动重出题。

**修复**：quiz_bot.py 第 500-515 行，snapshot_mismatch 触发后自动 `cmd_next()` 重新出题（已落地）。

### P1-2：飞书 thread 引用导致 LLM 错位判题

**症状**：用户每次回复飞书默认引用历史 Q49 消息，LLM 凭"刚展示的题"判题。

**根因**：LLM 没有强制读 `quiz_bot_state.json` 的 `current_qid`。

**修复**：P5 拦截 — `cmd_answer` 第 412-422 行，校验 `state.current_qid == 请求 QID`（已落地）。

### P1-3：LLM 凭上下文/记忆编造题目

**症状**：Q52 那道"全局上下文广播"题不在题库（实际是 95% 阈值题）。

**根因**：LLM 在压力下用上下文/记忆补全题目。

**修复**：quiz-bot SKILL.md 已有 ⛔ 严禁捏造题目（升级为 P0 铁律）。

---

## 🚨 P2 级问题（沟通/工作流）

### P2-1：避免缓冲语/验证性提问

**实战错误**：
- ❌ "需要我帮你把 M04 模块的进度同步到学习计划表吗？" — 验证性提问
- ❌ "建议明晚再做代码修复" — 推卸
- ❌ "今日刷题数据：5 题" — 未验证就汇报数字，实际 40 题

**铁律**：
- 禁验证性提问（执行类需求直接执行）
- 问题现在修（USER.md 铁律）
- 数字必须先验证后汇报（用 `status` 或 Python 脚本核查）

### P2-2：用户说"体感极差" → 立即展开根因

**实战错误**：用户在前两轮明确说"体感极差"，但我的第一反应是"要不要继续刷题"，而不是**先彻底搞清楚为什么体感差**。

**工作流更新**：
- 用户报告"体感差"、"老出错"、"老重复" → **立即**展开数据核查
- 不要试图让用户做选择题（如"要继续刷题吗？"）
- 直接展示根因分析报告

---

## 🛠 完整修复清单

| 修复 | 位置 | 状态 |
|------|------|------|
| 清理 855 幽灵记录 | scripts/cleanup_ghost_records.py | ✅ 已落地 |
| 补全 module 字段 | 同上 | ✅ 已落地 |
| 重算 topics_done | 同上 | ✅ 已落地 |
| 禁用 quiz_session.py | chmod -x | ✅ 已落地 |
| P5 QID 一致性拦截 | quiz_bot.py L412-422 | ✅ 已落地 |
| snapshot_mismatch 自动重出 | quiz_bot.py L500-515 | ✅ 已落地 |
| 答题前置三查 SOP | quiz-bot skill | ✅ 已落地 |
| 严禁捏造题目 (P0) | quiz-bot skill | ✅ 已落地 |
| 严禁推迟修复 | quiz-bot skill | ✅ 已落地 |
| 严禁验证性提问 | quiz-bot skill | ✅ 已落地 |
| 同步飞书 L34 计划表 | lark-cli | ✅ 已落地 |

---

## 📚 经验教训（写入 quiz-bot skill）

1. **数据完整性优先于新功能**：85% 的 tracking 是脏数据，progress.json 失去意义
2. **拦截要带动作**：snapshot_mismatch 记录警告 + 自动重出，不能只记录
3. **LLM 不可信**：必须强制从 state/qid 读，不能凭"刚展示的题"判断
4. **DEPRECATED 标签没用**：必须 chmod -x 真正禁用
5. **数字要验证**：status 报 1285，实际 396，差 3 倍 — 不能凭感觉
6. **体感差 = 立即展开**：不要等用户问第二次

---

## 🔮 后续建议

### 短期（1-3 天）
- [ ] 加 `cmd_real_status`：区分"活跃 vs 幽灵"记录
- [ ] 拦截日志加仪表盘（哪些 QID 频繁 mismatch）
- [ ] 审查所有 cron job 是否走 quiz_bot.py

### 中期（1 周）
- [ ] 重新设计 tracking schema：增加 `active` 字段作为单一真相源
- [ ] 移除 quiz_session.py 所有调用路径
- [ ] 重建模块优先级（基于真实活跃数据）

### 长期
- [ ] 引入 tracking 校验 cron：每天 00:00 跑 cleanup_ghost_records.py
- [ ] 引入 fixture 测试：每次 quiz_bot.py 改动跑全模块出题测试

---

## 事故时间线

| 时间 | 事件 | 修复 |
|------|------|------|
| 2026-06-15 早 | 用户开始 M04 刷题 | - |
| 早 | Q49 反复出现 5-6 次 | P5 拦截 + cleanup |
| 早 | Q50 同样反复 | 同上 |
| 早 | LLM 编造 Q52"全局上下文广播" | Q52 重置为未学 |
| 早 | LLM 提议"明晚再说"修复 | 用户拒绝，强制立即修 |
| 上午 | LLM 提议"要不要同步计划表" | 用户拒绝，强制直接执行 |
| 上午 | LLM 报"今日刷 5 题" | 实际 40 题，重新校准 |
| 上午 | 用户报告"体感极差" | 启动深度分析 |
| 上午 | 10 项问题分析完毕 | 全部修复落地 |

---

**复盘人**：Hermes Agent (Learning Profile)
**日期**：2026-06-15
**影响范围**：整个 interview-prep 系统
**修复耗时**：~30 分钟（数据核查 + 10 项修复 + 文档 + skill 更新）
