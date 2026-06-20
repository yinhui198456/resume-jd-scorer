# Quiz Bot 架构说明

## 与现有系统的关系

quiz_bot.py 和 ai-interview-prep skill + cron jobs **并行共存，不互相替代**。

| 组件 | 职责 | 触发方式 |
|---|---|---|
| ai-interview-prep skill | 20:15 推送 + 交互式教学（LLM 出题/判题） | cron / 用户对话 |
| daily-interview-bank-update (21:15) | 搜集新题 + 质量审计 + 架构检查 | cron |
| quiz_bot.py | **确定性**出题/判题（零幻觉） | 用户对话 |

**共享数据层**：`bank.json` + `progress.json`
**写入安全**：quiz_bot 使用文件锁（`fcntl.LOCK_EX`），与 cron 的 `update_daily_tracking.py` 不冲突

## 性能对比

| 指标 | LLM 方案 | quiz_bot.py |
|---|---|---|
| 响应时间 | ~15 秒 | < 0.1 秒 |
| 出题可靠性 | 可能凭记忆编造 | 100% 从 bank.json 读取 |
| 判题可靠性 | 可能回查 bank.json 导致逻辑断裂 | 确定性字符串比对 |

## 迁移策略

quiz_bot.py 是 ai-interview-prep 的**确定性替代方案**。当用户选择使用时：
1. 加载 `quiz-bot` skill（替代 `ai-interview-prep`）
2. 所有出题/判题走 quiz_bot.py
3. LLM 仅负责格式化展示 + "不会"时的教学讲解
4. ai-interview-prep skill 和 cron jobs 保持不变，继续运行
