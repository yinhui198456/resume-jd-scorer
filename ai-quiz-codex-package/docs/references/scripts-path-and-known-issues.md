# Scripts 路径约定与已知问题

## 路径约定

ai-interview-prep 的脚本位于 `skills/learning/ai-interview-prep/scripts/`，但 cron job 和日常调用需要从 `~/.hermes/profiles/learning/scripts/` 根目录执行。

**维护规则**：
- skill 目录的 `scripts/` 是权威源
- 每次修改后必须同步到 `~/.hermes/profiles/learning/scripts/`
- 同步命令：`cp skills/learning/ai-interview-prep/scripts/*.py scripts/`

## fix_length_bias.py 已知问题

### 1. answer 格式 bug（2026-05-31 修复）
- **症状**：`fix_length_bias.py` 修复 0 题，但 check_answer_quality.py 报 190 题 >1.8x
- **根因**：`find_correct_idx()` 用 `{'A': 0}.get(answer, -1)`，bank.json 中 answer 是 "A." 而非 "A"，永远返回 -1
- **修复**：`clean = answer.strip().rstrip("．。.").strip()` 后再查找

### 2. 修复质量不足
- 自动修复 190 题后仍有 128 题 >1.8x
- fallback 干扰项"工程实践表明..."被 check_answer_quality.py 检测为明显错误
- **结论**：极端长度偏见（如答案 120 字符 vs 干扰项 22 字符）无法靠概念反转修复，需人工重写

### 3. 干扰项质量
- build_distractors() 生成的干扰项缺乏领域专业性
- "该方案在实际生产环境中已被证明不可行" 等通用 fallback 质量差

## check_answer_exp_consistency.py 已知问题

### 1. 位置映射 bug（2026-05-31 修复）
- **症状**：报 70 处 answer/exp 不一致，但全部为假阳性
- **根因**：原代码假设选项以字母开头（如 "A. 正确答案"），用选项首字母作为字母标识。但实际选项可能以 `**`、`>` 或其他字符开头，导致解析错乱
- **修复**：改为 A=0/B=1/C=2/D=3 位置映射，直接按选项在数组中的索引位置判断，不再解析选项首字母
- **验证**：修复后真实 answer 标错 5 题（交互式刷题当场发现），假阳性 70→0

### 2. 检测局限
- 只能检测"explanation 包含某个非答案选项的完整文本"的情况
- 对于 answer 标签正确但 explanation 描述角度不同的情况无法检测
- **建议**：交互式刷题时人工 spot-check 新题

## architecture_self_check.py（2026-05-31 新增）

每日架构自检脚本，整合 5 项检查：
1. 题库质量 → audit + 长度偏见 + answer/exp 一致性
2. 防幻觉机制 → get_question.py / prepare_daily_quiz.py 可执行性
3. Cron 健康 → 20:15 推送状态
4. 数据一致性 → bank.json ↔ progress.json
5. 自动修复 → 孤儿记录清理

cron job `042e42c8a3dd` (21:15) 必须调用此脚本。
