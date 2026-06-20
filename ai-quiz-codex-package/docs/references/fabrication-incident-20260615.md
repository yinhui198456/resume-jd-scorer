# 2026-06-15 Q52 编造题事故 — 完整复盘

## 事故摘要

| 项目 | 详情 |
|------|------|
| **发生时间** | 2026-06-15 上午，M04_Context工程 刷题期间 |
| **症状** | 用户答 Q52 时选了 B，但实际题目被 LLM 捏造，不在题库 |
| **根因** | LLM 凭上下文/记忆凭空展示了一道"全局上下文广播"题，绕过了 quiz_bot.py |
| **影响** | Q52 学习完全无效；用户以为自己学了 4 题，实际只有 3 题 |
| **检测方式** | 用户反馈"50 题也是一样的" → LLM 主动核查 tracking 才发现 |

## 时间线

1. Q49 → Q50 → Q51 正常推进
2. Q52 展示时 LLM 没调 `next`，凭"上下文应该有这道题"捏造了"全局上下文广播"
3. 用户答 B → LLM 调用 `answer Q-M04_Context工程52 B`（QID 来自 state，但题目已被 LLM 篡改过展示内容）
4. 实际题库 Q52 是"Claude Code 95% 阈值压缩"题，答案也是 B
5. 答案碰巧对，但用户**学的内容**和**记录的内容**完全错位
6. 后续 Q53 正常推进时，用户反馈"50 题也是一样的"暴露问题

## 根因分解

### 根因 1（核心）：LLM 凭印象编造
- **触发条件**：连续刷题压力 + 上下文窗口膨胀
- **机制**：LLM 看到 Q49-Q51 连续 3 道 M04 题，预测 Q52 应该也是 M04 主题，凭"全局上下文广播是个合理的考点"补全了题目
- **关键失误**：没有在工具调用历史中确认"这行输出对应这道题"

### 根因 2：state.current_qid 没校验
- 当时 LLM 没有读 `tracking/quiz_bot_state.json` 验证 current_qid
- 也没有拦截机制阻止 `answer` 命令接受错位 QID

### 根因 3：模块锁定让用户感觉"刷题停滞"
- M04 锁定了 20+ 道题，next 一直在 M04 内部循环
- 增加了 LLM"凭印象"的风险

## 已落地修复（2026-06-15）

### 修复 1：P5 QID 错位拦截（quiz_bot.py）
位置：`cmd_answer` 函数
```python
# 2026-06-15 修复：answer 前置校验 state.current_qid 一致性
state = load_quiz_state()
state_qid = state.get('current_qid')
if state_qid and state_qid != qid:
    print(f"⚠️ P5 拦截：state.current_qid({state_qid}) ≠ 请求 QID({qid})")
    return
```
效果：用户答错位 QID 时直接拒绝，防止 tracking 污染。

### 修复 2：snapshot_mismatch 自动重出题（quiz_bot.py）
位置：`cmd_answer` 函数 snapshot_mismatch 分支
效果：state 状态不一致时自动调用 `next` 重新出题，而不是放行错位判题。

### 修复 3：Q52 重置为未学
- `tracking/progress.json` 中 Q-M04_Context工程52 已重置为 `first_learned: null`
- 下次 `next` 会重新出这道真实题让用户重做

### 修复 4：Skill 强化
- quiz-bot SKILL.md 新增"严禁捏造题目"P0 铁律章节
- 新增"答题前置三查"强制流程
- 新增"故障诊断：题目反复出现"排查表

## 历史同类事故对照

| 日期 | 事故 | 教训 |
|------|------|------|
| 2026-06-07 | 串题污染 tracking | 引入 hash 校验 |
| 2026-06-08（第一次）| Q-M06_MCP协议08~11 改写 | hash 拦截起效 |
| 2026-06-08（第二次）| 捏造 Q-M01_LLM基础74 | 凭上下文补全 |
| 2026-06-10（第三次）| Q-07/Q-24/Q-26/Q-27 全部编题 | P4 无法拦截出题环节 |
| **2026-06-15** | **捏造 Q-M04_Context工程52** | **QID 错位 + 编造双重失误** |

## 教训总结

### 给 LLM 的铁律
1. **每道展示给用户的题必须来自 `next` 输出** — 凭印象出题是 P0 违规
2. **答题前必查 state.current_qid** — 飞书 thread 引用 ≠ 当前题号
3. **连续 3 题以后特别警惕** — 上下文压力大，更容易凭印象补全
4. **题目对用户无意义时立即承认** — 不要硬撑，找下一题

### 给系统的兜底
- P5 QID 错位拦截已上线
- snapshot_mismatch 自动重出题已上线
- 后续可考虑：QID 校验失败的题目自动从学习统计中排除

## 验证方法

```bash
# 验证 P5 拦截生效
python3 scripts/quiz_bot.py --format md answer Q-M04_Context工程49 A
# 预期：⚠️ P5 拦截（因为 state QID 是 Q53）

# 验证正常判题
python3 scripts/quiz_bot.py --format md answer Q-M04_Context工程53 A
# 预期：✅ 正确

# 验证 Q52 重置成功
python3 -c "
import json
with open('tracking/progress.json') as f:
    p = json.load(f)
print(p['question_tracking']['Q-M04_Context工程52'])
"
# 预期：first_learned: None
```

## 关联文件

- `INCIDENT-20260615.md`（同目录）— 更高层的事故复盘
- quiz-bot SKILL.md "严禁捏造题目" 章节 — P0 铁律
- quiz-bot SKILL.md "答题前置三查" 章节 — 强制流程
- quiz_bot.py `cmd_answer` 函数 — P5 拦截实现
