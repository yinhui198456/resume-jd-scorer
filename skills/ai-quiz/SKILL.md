# AI刷题 Skill

## Purpose
用于每日 AI 知识点学习、题库抽题、答题记录、错题跟踪和学习进度维护。

## Shared Workspace
唯一工作目录：

/opt/personal-agent-workspace/ai-quiz-codex-package

不要复制数据到其他目录。所有读取、输出、写回都以该目录为准。

## Data Rules
1. 默认只读分析，不主动修改数据。
2. 需要修改题库、进度、错题、学习日志时，必须先说明将修改哪些文件、修改原因和影响范围。
3. 写入前必须等待用户确认。
4. 不允许删除历史学习记录。
5. 所有正式输出优先写入项目内既有 output、data/study-logs 或该项目约定目录。
6. 需要执行脚本时，必须先进入共享目录：
   cd /opt/personal-agent-workspace/ai-quiz-codex-package

## Concurrency Rules
多个飞书会话可能同时调用本 Skill。任何写操作必须先取得锁：

flock -x /opt/personal-agent-workspace/.locks/ai-quiz.lock -c '<写入命令>'

不能绕过锁直接写 data、题库、进度文件。

## Architecture

### Core Components

```
ai-quiz-codex-package/
├── engine/
│   └── quiz_engine.py      # 核心引擎：题目选择、去重、间隔复习、数据写入
├── tools/
│   ├── quiz_cli.py         # CLI 工具：启动会话、获取题目、提交答案
│   ├── sync_progress.py    # 同步工具：同步题库和进度
│   ├── get_question.py     # 单题获取工具
│   └── ...                 # 其他工具
├── data/
│   ├── question-bank/
│   │   └── bank.json       # 题库
│   ├── tracking/
│   │   ── progress.json   # 学习进度
│   └── study-logs/         # 学习日志
```

### Quiz Engine Features

**quiz_engine.py** 实现了以下核心功能：

1. **题目去重** (QuizSession.presented_questions)
   - 跟踪已展示但未提交的题目
   - 避免同一题目在同一会话中重复出现

2. **智能出题策略**
   - 错题优先 (confidence ≤ 2)
   - 到期复习优先
   - 薄弱模块优先 (进度 < 10%)
   - 轮换机制避免同一模块连续出题

3. **即时写入**
   - 每答完一题立即保存到 progress.json
   - 使用文件锁保证并发安全
   - 断线不丢失数据

4. **标准化输出**
   - 固定回复模板，减少变体
   - 正确答案: `✅ **正确！** 答案是 {answer}。`
   - 错误答案: `❌ **错误！** 正确答案是 **{answer}**。\n\n**解析**：{explanation}`
   - 不会回答: `正确答案是 **{answer}**。\n\n**解析**：{explanation}`

5. **修复的模块进度逻辑**
   - 只有新学题目才增加 topics_done
   - 所有题目都更新 last_studied
   - 明确区分新学和复习

### CLI Commands

```bash
# 启动刷题会话
python tools/quiz_cli.py start [mode]
# mode: mixed(默认), review, new, wrong

# 获取题目
python tools/quiz_cli.py get <mode> [limit] [modules...]
# mode: review, new, wrong, due

# 提交答案
python tools/quiz_cli.py submit <qid> <answer>
# answer: A/B/C/D/不会

# 查看统计
python tools/quiz_cli.py stats

# 查看会话信息
python tools/quiz_cli.py session-info
```

## Usage Workflow

### Standard Quiz Session

1. **启动会话**
   ```
   用户: 开始AI刷题
   Agent: python tools/quiz_cli.py start mixed
   ```

2. **逐题作答**
   ```
   用户: A
   Agent: python tools/quiz_cli.py submit Q-xxx A
   # 即时反馈，数据已保存
   ```

3. **查看进度**
   ```
   用户: 今天进度如何？
   Agent: python tools/quiz_cli.py stats
   ```

### Manual Mode (Legacy)

如果需要手动控制流程：

1. 使用 `engine/quiz_engine.py` 直接调用
2. 遵循 Data Rules 和 Concurrency Rules
3. 确保题目去重和即时写入

## Study Log Generation

学习日志自动生成路径：
`data/study-logs/reminder-{YYYY-MM-DD}.md`

包含内容：
- 今日答题概况
- 各轮次详情
- 错题汇总
- 薄弱模块
- 备注和建议

## Error Handling

1. **题目不存在**: 返回错误提示，不崩溃
2. **文件锁定失败**: 重试 3 次后报错
3. **数据损坏**: 从 backup 恢复（如果有）
4. **并发冲突**: 使用 flock 串行化写操作
