---
name: ai-quiz-codex
category: learning
description: AI 面试八股文刷题系统 — 完整迁移包，包含 quiz-bot、ai-interview-prep、question-bank-qa 三个 skill 的核心内容。
---

# AI 面试八股文刷题系统 — Codex 迁移版

> 整合 quiz-bot + ai-interview-prep + question-bank-qa 三个 skill 的核心内容。

## 核心原则

**所有出题/判题逻辑在 quiz_bot.py 中完成，LLM 只做原样转发和教学讲解。**

## 脚本接口

```bash
# 核心引擎
python3 engine/quiz_bot.py --format md next              # 下一道未学习题
python3 engine/quiz_bot.py --format md next M08_Agent架构 # 指定模块
python3 engine/quiz_bot.py --format md review             # 到期复习题
python3 engine/quiz_bot.py --format md answer <QID> <选项> # 判题
python3 engine/quiz_bot.py --format md skip <QID>          # 标记'不会'
python3 engine/quiz_bot.py explain <QID>                  # 获取解析
python3 engine/quiz_bot.py status                         # 进度
python3 engine/quiz_bot.py intercepts                     # Hash 拦截统计

# 质量工具
python3 tools/bank_checklist.py                           # 13 项质量扫描
python3 tools/check_answer_quality.py                     # 答案质量检测
python3 tools/check_answer_exp_consistency_v2.py          # 答案-解析一致性
python3 tools/check_distractor_quality.py                 # 干扰项质量
python3 tools/cleanup_ghost_records.py [--dry-run]        # 幽灵记录清理
python3 tools/sync_progress.py                            # 进度同步（只同步 total_topics，不创建空 tracking）
python3 tools/restructure_bank.py                         # 结构对齐

# 题库搜集
python3 tools/bank_collector.py --loop --target 35 --max-iter 10
python3 tools/bank_collector.py --status
```

## 交互铁律

### P0-0：严禁凭记忆编造题目
每一道展示给用户的题必须来自 `quiz_bot.py --format md next` 的实际输出。LLM 必须原样转发，不做任何改写。

### P0-1：进度数字必须验证后汇报
任何进度/统计数字必须先调 `status` 或 Python 脚本核查。

### P0-2：问题现在修，禁推迟
识别 quiz_bot.py 漏洞、判题错位、tracking 污染 → 当场修。

### P0-3：执行类需求直接执行，禁验证性提问
用户说"刷题" → 直接 `next`；答完题 → 主动 `next` 出下一题。

## 答题前置三查

收到用户 A/B/C/D 回复时：
1. 查 `tracking/quiz_bot_state.json` 的 `current_qid`
2. 查 QID 一致性
3. 用户回复是明确单字母（A/B/C/D）→ 一律用 `current_qid` 判题

## 模块锁定策略

- 无参数 `next`：自动锁定当前模块，至少连续刷 3 题
- 指定模块 `next M08_Agent架构`：强制锁定该模块
- SKIPPED_MODULES 在 `engine/quiz_bot.py` 顶部配置

## 艾宾浩斯复习

复习节点：第 1/3/7/14/30/90 天（6轮）
每道题独立追踪 confidence(1-5)、review_count、next_review、first_learned

`question_tracking` 使用 active-only 语义：只有已经学习、答过或 skip 的题才写入。不要为未学习题预创建 `first_learned: null` 的空记录。

## 质量保障

核心四件套（每次修改 bank.json 后必跑）：
```bash
python3 tools/check_answer_quality.py
python3 tools/check_answer_exp_consistency_v2.py
python3 tools/check_distractor_quality.py
python3 tools/bank_checklist.py
```

通过标准：0 Critical + 0 High

## 用户偏好

- 优先模块：M08 (Agent架构)、M07 (Agent框架)、M11 (RAG)
- 回避模块：M01 (LLM基础) — 默认在 SKIPPED_MODULES 中
- 解析长度：≤60 字
- 禁止：ASCII 架构图、表格（用列表替代）

## 文件结构

```
ai-quiz-codex/
├── engine/quiz_bot.py          # 核心引擎（915行）
├── data/
│   ├── question-bank/bank.json  # 题库（1409题/19模块/1.7MB）
│   └── tracking/                # 学习进度
├── tools/                       # 质量工具脚本
├── docs/references/             # 历史事故分析
└── README.md                    # 详细说明
```

详见 README.md 获取完整文档。
