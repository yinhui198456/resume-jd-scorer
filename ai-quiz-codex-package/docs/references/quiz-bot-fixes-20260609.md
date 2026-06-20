# Quiz Bot 系统性修复（2026-06-09）

## 触发场景

近1小时刷题中发现 50% 题目被 P4 Hash 校验误拦截 + 「不会」题目不进复习队列 + 模块碎片化（10模块各刷1-2题）。用户要求"修复所有问题 + subagent 验证"。

## 修复清单

### P0：新增 `skip` 命令

**问题**：用户说"不会" → explain → 下一题。题目不在 progress.json 中，永远不会复习。

**修复**：`cmd_skip(qid)` — 写入 progress.json（confidence=1, result=skipped），进入正常复习队列。

**代码**：L149-L218

### P0：P4 Hash 校验竞态修复

**问题**：state 是全局单例，连续 `next` 覆盖快照 → snapshot_mismatch 误拦截 ~50% 题目。

**修复**：
- `log_hash` 作为唯一权威源（不可变追加，不匹配=题库被修改）
- `snapshot_mismatch` 不再拒绝用户，仅记录警告
- 新增 `_log_intercept()` 记录到 `quiz_intercept_log.jsonl`

**代码**：L420-L454（验证逻辑）+ L132-L146（拦截日志）

### P1：模块锁定策略

**问题**：Hash 拦截后被迫换模块 → 10模块各刷1-2题。

**修复**：`quiz_bot_state.json` 记录 `locked_module` + `module_question_count`。每模块至少连续刷 3 题。

**代码**：L242-L315

### P1：拦截可观测性

**问题**：无法回答"哪些题被拦截了、为什么"。

**修复**：`cmd_intercepts()` — 读取 `quiz_intercept_log.jsonl` 输出统计。

**代码**：L698-L743

### P2：统一双引擎

**问题**：quiz_bot.py 与 quiz_session.py 双引擎冲突，schema 不一致。

**修复**：quiz_session.py 头部标记 DEPRECATED，2026-07-01 移除。

## Subagent 发现的额外 Bug

### Bug 8：`_output_question` 覆盖 state

**问题**：`save_quiz_state(state_data)` 用新字典直接覆盖整个 state，丢失 `locked_module` 和 `module_question_count`。

**修复**：`existing_state = load_quiz_state()` → `existing_state.update(state_data)` → 保存。md 和 pipe 两个分支均已修复。

### Bug 9：显式模块切换失效

**问题**：`next M02_Transformer` 仅设置 `locked_mod` 但 fall through 到遍历所有模块。

**修复**：在 `if module_partial:` 分支中增加 `_find_q_in_module` 找题，找到后直接输出并 return。

## 验证结果

3 个 subagent 并行验证：
1. **功能验证**：skip / intercepts / 语法检查 → ✅ 全部通过
2. **逻辑验证**：P4 竞态场景 + 模块锁定（10 测试用例）→ ✅ 10/10 通过
3. **端到端**：完整刷题流程（next→answer→skip→review）→ ✅ 全部通过

## 待优化项

**review 排序策略**：当前按到期日期排序，未按信心优先级。信心 1/5 的 skipped 题不会被特别优先。建议在排序中加入 confidence 权重。
