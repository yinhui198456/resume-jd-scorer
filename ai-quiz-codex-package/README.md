# AI 面试八股文刷题系统

> 专为 AI 应用工程师面试准备的确定性刷题系统。LLM 零幻觉 — 所有出题/判题由 Python 脚本完成，LLM 只做原样转发和教学讲解。

## 系统概览

```
ai-quiz-codex/
├── engine/                  # 核心引擎
│   └── quiz_bot.py         # 确定性出题/判题引擎（915行，32KB）
├── data/                    # 数据文件
│   ├── question-bank/       # 题库（1409题 / 19模块 / 1.7MB）
│   │   ├── bank.json       # 主题库文件
│   │   └── changelog.md    # 更新日志
│   ├── tracking/            # 学习进度追踪
│   │   ├── progress.json           # 艾宾浩斯复习数据
│   │   ├── quiz_bot_state.json     # 当前会话状态
│   │   ├── quiz_hash_log.jsonl     # Hash 校验日志
│   │   └── quiz_intercept_log.jsonl # 拦截事件日志
│   └── study-logs/          # 每日学习日志
├── tools/                   # 辅助工具脚本
│   ├── bank_checklist.py           # 题库质量检查（13项扫描）
│   ├── bank_collector.py           # 题库搜集循环控制器
│   ├── prepare_daily_quiz.py       # 每日 quiz 推送准备
│   ├── quality_gate.py             # 质量门控
│   ├── get_question.py             # 旧版出题脚本（已废弃，保留兼容）
│   ├── check_answer_quality.py     # 答案质量检测
│   ├── check_answer_exp_consistency_v2.py  # 答案-解析一致性
│   ├── check_distractor_quality.py # 干扰项质量扫描
│   ├── shuffle_answers.py          # 选项打乱
│   ├── restructure_bank.py         # 结构对齐（ID统一）
│   ├── sync_progress.py            # 进度同步
│   ├── architecture_self_check.py  # 架构自检
│   └── cleanup_ghost_records.py    # 幽灵记录清理
├── docs/                    # 文档
│   ├── SKILL.md            # 综合 Skill 文档（3个 Skill 合并）
│   └── references/          # 历史事故分析与设计文档
└── README.md               # 本文件
```

## 快速开始

### 基本用法

```bash
# 出题（下一道未学习题）
python3 engine/quiz_bot.py --format md next

# 指定模块出题
python3 engine/quiz_bot.py --format md next M08_Agent架构

# 复习到期题目
python3 engine/quiz_bot.py --format md review

# 判题
python3 engine/quiz_bot.py --format md answer Q-M08_Agent架构01 A

# 标记"不会"
python3 engine/quiz_bot.py --format md skip Q-M08_Agent架构01

# 查看进度
python3 engine/quiz_bot.py status

# 查看 Hash 拦截统计
python3 engine/quiz_bot.py intercepts
```

### 交互流程

```
出题 → 等待用户回答 → 判题 → 出下一题 → 循环
```

**铁律**：
1. 每道题必须从 `quiz_bot.py --format md next` 获取，禁止 LLM 凭记忆编造
2. LLM 必须原样转发脚本输出，禁止改写/重组/解释题目
3. 用户回答后必须先判题再出下一题，禁止跳过 tracking
4. 每道题独占一条消息，出题后必须 STOP 等待用户回复

## 核心设计

### 防幻觉体系

| 防护层 | 机制 | 说明 |
|--------|------|------|
| P0 | 零 LLM 参与出题 | 脚本输出是唯一事实源 |
| P1 | topics_done 答对+1 | 模块进度准确 |
| P2 | MD5 Hash 校验 | 出题时生成 hash，判题时比对 |
| P3 | 完整答案文本 | 判题输出含正确选项全文 |
| P4 | 三源校验 | log hash 为不可变权威源 |
| P5 | QID 一致性检查 | state.current_qid ≠ 请求 QID 拒绝判题 |

### 艾宾浩斯复习

复习间隔：第 1/3/7/14/30/90 天（6轮）

每道题独立追踪：
- `confidence`：1-5 分
- `review_count`：已复习轮数
- `next_review`：下次复习日期
- `first_learned`：首次学习日期

`question_tracking` 采用 **active-only** 语义：只有已经学习、答过或 skip 的题目才写入 tracking。未学习题不应预创建 `first_learned: null` 的空记录，否则会和幽灵记录清理逻辑冲突。

### 题库结构

```json
{
  "meta": {
    "total_questions": 1409,
    "last_updated": "2026-06-18"
  },
  "modules": {
    "M08_Agent架构": {
      "questions": [
        {
          "id": "Q-M08_Agent架构01",
          "question": "题干文本",
          "options": ["A文本", "B文本", "C文本", "D文本"],
          "answer": "A",
          "explanation": "解析文本",
          "difficulty": "medium",
          "tags": ["agent", "architecture"]
        }
      ]
    }
  }
}
```

### 19 个模块

| 优先级 | 模块 | 题数范围 |
|--------|------|----------|
| 高 | M03 Prompt工程、M04 Context工程、M05 FunctionCalling、M06 MCP、M07 Agent框架、M08 Agent架构、M09 框架选型、M10 MultiAgent、M11 RAG | 70-88 |
| 中 | M13 安全评估、M14 推理部署、M15 成本优化、M16 AgenticCoding、M17 工程化、M18 系统设计 | 70-85 |
| 低 | M01 LLM基础、M02 Transformer、M12 Memory、M19 VLM多模态 | 70-80 |

## 质量保障

### 核心四件套（每次修改题库后必跑）

```bash
python3 tools/check_answer_quality.py              # 多答案 + 干扰项明显 + 长度偏见
python3 tools/check_answer_exp_consistency_v2.py   # 答案与解析一致性
python3 tools/check_distractor_quality.py          # 长度偏见独立扫描
python3 tools/bank_checklist.py                    # 全量 13 项检查
```

通过标准：0 Critical + 0 High 即达标。

### 质量检查分级

- **Critical**：答案标错、选项完全重复、整题损坏 → 立即修复
- **High**：模板后缀、选项截断 → 尽快修复
- **Medium**：绝对化措辞、长度偏差 → 后续优化
- **Low**：缺 difficulty 字段 → 有空再补

### 已知破坏性脚本（已废弃，禁止恢复）

- `quick_fix_quality.py` — 追加填充语导致跨题重复
- `deep_rebuild_bank.py` — 硬编码模板生成干扰项
- `fix_length_bias.py` — 只治长度不治语义
- `fix_filler_patterns.py` — 替换一种 filler 为另一种

## 用户偏好

- **优先模块**：M08 (Agent架构)、M07 (Agent框架)、M11 (RAG)
- **回避模块**：M01 (LLM基础) — 默认跳过
- **学习方向**：AI 应用工程师（非预训练研究）
- **交互风格**：直接执行，禁止验证性提问；问题当场修，禁止推迟
- **解析长度**：≤60 字，2-3 句话
- **禁止**：ASCII 架构图（用 Mermaid 替代）、表格（用列表替代）

## 模块跳过配置

在 `engine/quiz_bot.py` 顶部修改：

```python
SKIPPED_MODULES = ['M01_LLM基础', 'M02_Transformer']  # 屏蔽
SKIPPED_MODULES = []  # 恢复全部
```

## 数据修复

### 幽灵记录清理

```bash
python3 tools/cleanup_ghost_records.py --dry-run   # 预览
python3 tools/cleanup_ghost_records.py             # 执行
```

### 进度同步

```bash
python3 tools/sync_progress.py  # 对齐 total_topics 与 bank.json 题数
```

`sync_progress.py` 只同步 `modules_progress[*].total_topics` 并报告孤儿记录；不会为题库中的未学习题创建空 tracking 记录。

### 结构对齐（ID 格式混乱时）

```bash
python3 tools/restructure_bank.py  # ID 统一 + 连续编号 + tracking 迁移
```

## 题库搜集

```bash
python3 tools/bank_collector.py --loop --target 35 --max-iter 10  # 启动搜集循环
python3 tools/bank_collector.py --status                          # 查看各模块题数
python3 tools/bank_collector.py --inject file.json --source ID --module M08_Agent架构  # 导入
```

数据源优先级：Y44 共享数据 > 牛客面经 > GitHub raw > web_search

## 关键文件说明

### engine/quiz_bot.py

核心引擎，915 行，负责：
- 出题（新题/复习/指定模块）
- 判题（A/B/C/D 比对）
- 进度更新（带文件锁的安全写入）
- 质量门控（自动跳过不合格题目）
- Hash 校验（防串题）

### tools/bank_checklist.py

13 项质量扫描：
1. 多个正确答案检测
2. 干扰项过于明显
3. 长度偏见 >1.8x
4. 答案-解析一致性
5. B/C 近重复（Jaccard >0.9）
6. 万能填充词检测
7. 题干格式检查
8. Answer/Exp 串题检测
9. key_concepts 有效性
10. 短语式题干检测
11. 选项完全相同
12. 修复后遗症检测
13. ID-内容一致性

### tools/bank_collector.py

题库搜集循环控制器：
- 选源→选模块→质量检查→去重→入库→评分
- 源自适应：通过率高的源自动优先
- Pre-flight 质量门控
- 循环停止：所有模块达标或达到 max_iter

## 历史事故记录

详见 `docs/references/` 目录，包含：
- 编造题事故分析（2026-06-07, 06-08, 06-10, 06-15）
- Hash 拦截问题分析
- 串题事故复盘
- 系统性问题深度复盘
- 修复方案验证报告

## 迁移到 Codex 使用

### 环境要求

- Python 3.8+
- 无外部依赖（纯标准库 + json）

### 在 Codex 中运行

1. 将整个项目目录放入 Codex 工作空间
2. 所有路径使用相对路径（基于项目根目录）
3. 确保 `engine/`、`data/`、`tools/` 目录结构完整
4. 运行命令从项目根目录执行：

```bash
# 出题
python3 engine/quiz_bot.py --format md next

# 判题
python3 engine/quiz_bot.py --format md answer Q-M08_Agent架构01 A

# 质量检查
python3 tools/bank_checklist.py
```

### 注意事项

1. **quiz_bot.py** 使用相对路径查找 `data/question-bank/bank.json` 和 `data/tracking/`
2. 如果需要修改路径，编辑 `quiz_bot.py` 顶部的 `BANK_PATH`、`PROGRESS_PATH` 等常量
3. 数据文件较大（bank.json 1.7MB, progress.json 483KB），首次加载可能需要几秒
4. 文件锁（fcntl）确保与 cron 任务不冲突

## 版本信息

- 题库：1409 题 / 19 模块（截至 2026-06-18）
- quiz_bot.py：915 行（2026-06-15 最终版本）
- 累计修复：430+ Critical/High 质量问题
- 质量状态：Critical 0、High 0、Medium ~186（历史遗留，不影响答题）
