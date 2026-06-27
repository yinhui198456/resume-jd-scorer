---
name: ai-quiz
description: 当用户说“开始AI刷题”、“刷题”、“下一题”，回答 A/B/C/D/不会，或询问 AI 刷题进度、错题、复习计划时使用。维护 AI 题库、学习进度、即时判题、复习调度和学习日志；所有项目代码和数据以 /opt/personal-agent-workspace/ai-quiz-codex-package 为准。
---

# AI刷题 Skill

##  重要：代码位置

**所有代码统一维护在工作区**：
- Skill 定义：`/opt/personal-agent-workspace/skills/ai-quiz/SKILL.md`
- 项目代码：`/opt/personal-agent-workspace/ai-quiz-codex-package/`

CC 通过 `~/.claude/skills/ai-quiz/SKILL.md` 访问（此文件应与工作区保持同步）。

**同步命令**：
```bash
cp /opt/personal-agent-workspace/skills/ai-quiz/SKILL.md ~/.claude/skills/ai-quiz/SKILL.md
```

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
/opt/personal-agent-workspace/
├── skills/
│   └── ai-quiz/
│       └── SKILL.md          # Skill 定义（统一维护位置）
└── ai-quiz-codex-package/
    ├── engine/
    │   └── quiz_engine.py    # 核心引擎
    ├── tools/
    │   └── quiz_cli.py       # CLI 工具
    ├── data/
    │   ├── question-bank/
    │   │   └── bank.json
    │   ├── tracking/
    │   │   └── progress.json
    │   └── study-logs/
    └── docs/
        ├── CODE_REVIEW.md
        └── 修复总结.md
```

### Usage

```bash
# 启动刷题会话
cd /opt/personal-agent-workspace/ai-quiz-codex-package
python tools/quiz_cli.py start mixed

# 提交答案
python tools/quiz_cli.py submit Q-xxx A

# 查看统计
python tools/quiz_cli.py stats
```

## Code Review
详见 `docs/CODE_REVIEW.md`

## 修复总结
详见 `docs/修复总结.md`
