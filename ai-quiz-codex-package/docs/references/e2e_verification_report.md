# E2E 端到端验证报告 — quiz_bot.py 完整用户流程

**测试日期:** 2026-06-09  
**测试对象:** `scripts/quiz_bot.py` (5 项修复后的版本)  
**工作目录:** `/root/.hermes/profiles/learning/workspace/interview-prep/`

---

## 验证项目与结果

### 1. ✅ 备份与恢复
- 备份了 `progress.json`、`quiz_bot_state.json`、`quiz_hash_log.jsonl`、`quiz_intercept_log.jsonl`
- 测试完成后成功恢复，状态与测试前一致

### 2. ✅ `next` 命令 — 出新题
- **第一次 `next`:** 返回 Q-M01_LLM基础79 (M01 模块)
- **第二次 `next`:** 返回 Q-M02_Transformer06 (M02 模块)
- **第三次 `next`:** 返回 Q-M02_Transformer07 (M02 模块)
- `next` 正确跳过已学习题目和质量不合格题目

### 3. ✅ `answer` 命令 — 判题
- `answer Q-M01_LLM基础79 A` → ✅ 正确，confidence 3→4，next_review=2026-06-12
- `answer Q-M02_Transformer06 A` → ✅ 正确，confidence 3→4，next_review=2026-06-12
- P4 Hash 校验正常工作，未出现误拦截

### 4. ✅ 模块锁定策略
- **M01 锁定行为:** M01 仅剩 1 道可用题 (Q79，另一道 Q67 因"面试建议"被过滤为开放题)。Q79 答完后 M01 耗尽 → 自动解锁，切换到 M02。**行为正确。**
- **M02 锁定行为:** Q-M02_Transformer06 答完后，state 中 `locked_module=M02_Transformer`, `module_question_count=1`。第二次 `next` 仍在 M02 出 Q-M02_Transformer07，`module_question_count=2`。**锁定生效。**
- 由于 M02 还有 32+ 道未学习题目，锁定会持续直到 3 题完成或模块耗尽

### 5. ✅ `skip` 命令 — 标记不会
- `skip Q-M02_Transformer07` 输出:
  ```
  SKIP|Q-M02_Transformer07
  CONFIDENCE|1/5
  NEXT_REVIEW|2026-06-12
  ```
- **progress.json 验证:**
  - `first_learned`: 2026-06-09 ✅
  - `confidence`: 1 ✅
  - `status`: learning ✅
  - `result`: skipped ✅
  - `wrong_count`: 1 ✅
  - `review_count`: 1 ✅
  - `next_review`: 2026-06-12 ✅
  - `module`: M02_Transformer ✅

### 6. ✅ `review` 命令 — 复习 skipped 题
- 隔离 Q-M02_Transformer07 为唯一到期复习题后，`review` 正确返回该题
- **信心 1/5 的题目能进入复习队列** ✅
- **注意:** review 命令按 `next_review` 日期排序（最早到期的优先），**不是**按 confidence 排序。如果有多个到期题目，信心低的题目不会被特别优先。这是当前实现的设计选择。

### 7. ✅ `intercepts` 命令 — 拦截统计
- 输出: `INTERCEPTS|共 1 次拦截`
- 原因: `snapshot_mismatch_warn: 1次`
- 被拦截题目: `Q-M15_成本优化01: 1次`
- 命令正常工作 ✅

### 8. ✅ P4 Hash 校验 — 不拦截正常答题
- 整个流程中所有 `answer` 命令均未触发拦截
- `snapshot_mismatch` 不再作为独立拒绝条件（P0 修复生效）

---

## 发现的问题

### 问题 1: review 排序未优先低信心题
- **现象:** `cmd_review` 按 `next_review` 日期排序 (`due.sort(key=lambda x: x[1])`)，而非按 confidence 排序
- **影响:** 信心 1/5 的 skipped 题如果到期日较晚，不会比信心 5/5 但到期日更早的题目优先
- **建议:** 可考虑在多因子排序中加入 confidence 权重，例如 `due.sort(key=lambda x: (x[1], -tracking[x[0]].get('confidence', 5)))`

### 问题 2: M01 模块仅剩 1 道可用题
- M01 有 79 题，其中 77 题已学习，1 题 (Q67) 被开放题过滤，仅剩 Q79
- 这是数据层面的问题，不影响模块锁定逻辑的正确性

### 问题 3: `review_count` 在测试中被意外修改
- 在 review 隔离测试中，为隔离单个题目，脚本将其他题目的 `review_count` 设为 6
- 这覆盖了之前 `answer` 命令设置的正确值
- **仅影响测试环境**，已通过恢复备份修复

---

## 结论

**5 项修复全部通过端到端验证:**

| 修复项 | 验证结果 |
|--------|----------|
| P0: skip 命令 | ✅ 写入 progress，confidence=1，进入复习队列 |
| P0: P4 Hash 校验修复 | ✅ snapshot_mismatch 不再拦截答题 |
| P1: 模块锁定策略 | ✅ 连续出题在同一模块，模块耗尽自动解锁 |
| P5: intercepts 命令 | ✅ 正常输出拦截统计 |
| P0: _output_question state 覆盖修复 | ✅ state 中 locked_module 和 module_question_count 在 output 后保留 |

**系统状态已恢复到测试前，所有备份已清理。**
