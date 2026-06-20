# Quiz Session Accidents — 2026-06-07

## 事故时间线

| 时间 | 症状 | 根因 | 修复 |
|------|------|------|------|
| Q36 答完 | Agent 编造 Q-M08_Agent架构37（不存在） | `next_in_module` 返回 COMPLETE，LLM 在空白期凭记忆编题 | 给 `get_question.py` 加了 `auto_next` 命令 |
| Q04-Q12 之间 | Agent 展示的题目与 bank.json 实际内容完全不符（串题） | Agent 自行"润色/改写"脚本输出，改写中混淆了多道题 | 强制 `--format md` 原样转发 |
| Q16 判题 | 展示 "Thin Wrapper" 题，但题库 Q16 实际是 "RetrievalQA Chain" | 同上，改写幻觉 | 同上 |
| Q28 选项 | 展示选项与 bank.json 不一致 | Agent 未用脚本输出，凭记忆生成选项 | 强制脚本取题 |

## 根因分析

**编题**：`COMPLETE` 返回纯文本字符串，LLM 缺乏结构化"下一步"信号 → 在推进流程压力下产生幻觉。
**串题**：LLM 收到脚本输出后自行"润色"，润色过程中混淆了记忆中多道题的内容。
**数据错位**：`progress.json` 的 `total_topics` 与 `bank.json` 实际题数不一致（今天新增题未同步）。

## 修复清单

1. **代码**：`get_question.py` 增加 `auto_next` 命令 + `get_next_auto_switch()` 函数
2. **数据**：`progress.json` 的 `total_topics` 与 `bank.json` 对齐（12 个模块更新）
3. **流程**：判题后必须立即调用 `update_daily_tracking.py` 或手动补录

## 当 update_daily_tracking.py 失败时的备用方案

`update_daily_tracking.py` 要求 QID 已存在于 tracking 中，对新题会报警 "not in tracking, skipping"。

备用方案（execute_code 直接修改 progress.json）：
```python
import json
path = '/root/.hermes/profiles/learning/workspace/interview-prep/tracking/progress.json'
with open(path) as f:
    p = json.load(f)
p['question_tracking'][qid] = {'first_learned': '2026-06-07'}
mod = p['modules_progress'][module_name]
mod['topics_done'] = mod.get('topics_done', 0) + 1
with open(path, 'w') as f:
    json.dump(p, f, ensure_ascii=False, indent=2)
```

## 事故补充：M10 串题（2026-06-07 晚）

**症状**：Agent 在 M09 模块完成后，自动切到 M10 MultiAgent 模块，但连续出了两道题（Q09 "松耦合通信模式"、Q10 "Supervisor 模式"），**题目内容完全不是 bank.json 里的实际题目**。

- Agent 展示的 Q09：松耦合通信模式 → bank.json 实际是「MetaGPT SOP-as-Code 理念」
- Agent 展示的 Q10：Supervisor 模式 → bank.json 实际是「Orchestrator-Worker 模式」

**根因**：Module 切换时（Q-M09 → Q-M10），Agent **没有执行任何脚本或 execute_code 读取 bank.json**，直接在 LLM 侧凭上下文/记忆生成了两道看似合理的 M10 题目。

**与之前事故的区别**：
- 之前的编题发生在 `COMPLETE` 信号后（LLM 不知道下一步该做什么）
- **这次发生在正常模块切换过渡中**——即使有明确的模块切换逻辑，LLM 仍会跳过脚本取题环节

**修复**：Agent 自查发现不一致后，执行 execute_code 重新读取 bank.json，展示了正确题目。

**铁律补充**：**任何模块切换（包括 auto_next 自动切换）后出的第一题，必须 execute_code 从 bank.json 读取验证。** 不能因为是"自动切换"就跳过取题步骤。

## 用户反馈原话

- 「不是太理解，为什么是今晚改 quiz_bot.py 和脚本逻辑，而不是现在？」
- 「有问题为什么不改？」
- 「确定上面的问题都修复了？要不要用 subagent 再自检一遍？」
