# 周末午餐方案生成系统 (Weekend Lunch Plan System)

> v4.1 — 面向 Codex / 独立 Agent 的完整菜谱 SOP 系统

## 概述

这是一个完整的周末午餐方案生成系统，包含数据预检、多轮审核（自动审核门 + 三 subagent 对抗审查 + 聚合裁决）、菜谱推荐、数据持久化等全流程 SOP。

设计目标：为家庭（中度脂肪肝成人 + 青春期儿童 + 幼儿）生成健康、美味、可操作的午餐方案（2大荤 + 1素/小荤 + 1汤 + 1主食，≤45分钟）。

## 项目结构

```
weekend-lunch-plan-codex/
├── README.md                    # 本文件
├── AGENTS.md                    # Codex 项目指引：提示“周末午餐建议”使用本 skill
├── tests/                       # TDD/回归测试
└── .agents/skills/weekend-lunch-plan/
    ├── SKILL.md                 # 主 SOP 文档（Codex 可发现的 skill 入口）
    ├── scripts/
    │   ├── recipe_preflight.py      # SOP 1: 数据预检（黑名单/库存/意向池/feedback）
    │   ├── recipe_review_gate.py    # SOP 1.5: 自动审核门（10项纯规则检查）
    │   ├── recipe_eval_aggregator.py # SOP 1.5: 聚合裁决（PASS/FAIL/FALLBACK）
    │   ├── review_pipeline.py       # 审核流水线（审核门 + 三方评估聚合）
    │   ├── record_plan.py           # 方案确认后写入 history.json
    │   ├── record_feedback.py       # 饭后写入 dish_feedback.json
    │   └── feedback_reminder.py     # 输出待反馈菜品列表
    ├── templates/
    │   ├── eval-validator.md        # 校验官 subagent prompt（结构/排重/口味/热门验证）
    │   ├── eval-chef.md             # 厨师 subagent prompt（时间/器具/人力/烹饪常识）
    │   ├── eval-redteam.md          # 红队 subagent prompt（对抗审查/成分/类别/创意真实性）
    │   └── feedback-cron.example    # 反馈提醒 cron 示例
    ├── references/
    │   ├── quality-checklist.md     # 主 agent 自检前置清单（16节）
    │   ├── popular-dishes.md        # 热门菜品参考表（已验证，含7月时令）
    │   ├── dish-technique-notes.md  # 详细做法参考（高分菜谱精确步骤）
    │   ├── cooking-research-notes.md # 烹饪研究笔记（网友教训汇总）
    │   ├── chef-review-cases.md     # 厨师审核实战案例（6个案例）
    │   ├── audit-case-2026-06-06.md # 历史审计案例
    │   ├── culinary-craft-review.md # 烹饪工艺审查参考
    │   ├── consistency-audit.md     # 技能一致性审计日志
    │   ├── session-2026-06-15-review.md # 历史复盘记录
    │   └── lark-cli-pitfalls.md     # 飞书CLI陷阱（归档，Codex环境可选）
    └── data/                    # 数据文件模板（首次运行需创建）
        ├── history.json.example
        ├── inventory.json.example
        ├── wishlist.json.example
        └── dish_feedback.json.example
```

## 相关 Skill（已合并入本包）

以下内容来自 `recipe-food-safety` 和 `recipe-sop-discipline` skill，已合并到 `.agents/skills/weekend-lunch-plan/SKILL.md` 和其 `references/` 中：

- **食品安全审核清单**（海鲜杀菌/焯水换水/高压锅时间/调料量化/豆腐蛋液熟度）
- **烹饪工艺审核要点**（白炒/锅塌/红烧/清蒸/焯水/烤蔬菜等技法定义）
- **红队审计实战案例**（同安封肉+白炒鲜贝+锅塌豆腐全流程审计）
- **SOP 执行纪律**（禁止跳步/质量>速度/预检脚本为唯一数据源）

## 快速开始

### 1. 准备数据文件

将 skill 内 `data/` 目录下的 `.example` 文件复制到实际数据目录（默认为 `~/.hermes/profiles/life/data/`，可通过 `RECIPE_DATA_DIR` 自定义），去掉 `.example` 后缀：

```bash
export RECIPE_DATA_DIR=<DATA_DIR>
mkdir -p "$RECIPE_DATA_DIR"
cp .agents/skills/weekend-lunch-plan/data/history.json.example "$RECIPE_DATA_DIR/history.json"
cp .agents/skills/weekend-lunch-plan/data/inventory.json.example "$RECIPE_DATA_DIR/inventory.json"
cp .agents/skills/weekend-lunch-plan/data/wishlist.json.example "$RECIPE_DATA_DIR/wishlist.json"
cp .agents/skills/weekend-lunch-plan/data/dish_feedback.json.example "$RECIPE_DATA_DIR/dish_feedback.json"
```

或创建空数组 `[]` 的文件。

### 2. 运行预检脚本

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/recipe_preflight.py
```

输出 JSON 格式的预检报告，包含黑名单、可用食材、意向池、feedback、采购建议。

### 3. 生成方案

在 Codex 中推荐直接发指令：

```text
周末午餐建议
```

Codex 会通过 `.agents/skills/weekend-lunch-plan/SKILL.md` 的描述隐式匹配本 skill。首次迁移后请重启 Codex 或开启新会话，让 Codex 重新扫描 `.agents/skills`。若想确保触发，可显式写：

```text
$weekend-lunch-plan 周末午餐建议
```

Codex 应按 skill SOP 生成 3 套初稿方案，并调用本 skill 的脚本完成预检和审核。下面的脚本命令主要用于调试、验收或手工 fallback。

### 4. 自动审核

```bash
# 将方案 JSON 通过 stdin 传入审核门
cat plan.json | python3 .agents/skills/weekend-lunch-plan/scripts/recipe_review_gate.py
```

返回 PASS 则进入 subagent 审核，返回 FAIL 则修正后重跑。

也可以使用流水线脚本先跑审核门，再输出三方审核模板路径：

```bash
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/review_pipeline.py
```

### 5. 三 Subagent 审核

按 `templates/` 中的 prompt 模板启动 3 个并行审核 agent（校验官/厨师/红队）。

### 6. 聚合裁决

```bash
# 将 3 个评估结果通过 stdin 传入
cat evals.json | python3 .agents/skills/weekend-lunch-plan/scripts/recipe_eval_aggregator.py --stdin
```

或交给流水线脚本聚合：

```bash
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/review_pipeline.py --evals evals.json
```

全部通过 → 交付给用户；任一不通过 → 修正后重跑（最多3次）。

### 7. 方案确认后写入历史

用户确认某套方案后，将该方案菜名写入 `history.json`，用于后续 30 天排重：

```bash
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/record_plan.py --selected 方案A
```

### 8. 饭后记录反馈

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/record_feedback.py --dish 清蒸多宝鱼 --rating love --note "孩子喜欢"
RECIPE_DATA_DIR=<DATA_DIR> python3 .agents/skills/weekend-lunch-plan/scripts/feedback_reminder.py --days 7
```

## 核心约束

- **健康基线**：中度脂肪肝（低油低糖）、儿童高钙/高锌/高蛋白
- **菜品结构**：2大荤 + 1素/小荤 + 1汤 + 1主食
- **总制作时间**：≤ 45 分钟
- **口味**：江浙清淡无辣，不喜甜，几乎不吃辣
- **烹饪熟练度**：新手/不熟练（优先简单刀工、基础调味、宽松火候）
- **永久排除**：苦瓜、辣味菜、甜口菜、5-9月温燥食材（羊肉/狗肉/鹿肉）
- **特色度**：每套至少1道菜有"餐厅感"（食材组合讲究/烹饪手法多样/仪式感）

## 审核架构

```
方案生成 → 自动审核门(10项规则) → FAIL? 驳回修正
    ↓ PASS
主 agent 自检(quality-checklist.md)
    ↓
3 subagent 并行审核
  ├── 校验官：结构/排重/黑名单/口味/热门验证/当季创意
  ├── 厨师：时间/器具冲突/人力负荷/烹饪常识
  └── 红队：成分/类别一致性/创意真实性/去重/定位
    ↓
聚合裁决(PASS/FAIL/FALLBACK)
    ↓
全部通过 → 交付用户
```

## Codex 适配说明

### 与原版 Hermes 环境的差异

| 功能 | 原版 (Hermes) | Codex 环境 |
|------|--------------|-----------|
| Subagent 审核 | `delegate_task()` | Codex 的 subagent/spawn 机制 |
| 数据文件路径 | `~/.hermes/profiles/life/data/` | 自定义，通过 `RECIPE_DATA_DIR` 环境变量 |
| 飞书文档归档 | `lark-cli` | 可选发布目标，主流程不依赖 |
| Cron 反馈提醒 | Hermes cronjob | 使用 `templates/feedback-cron.example` 配置外部调度 |

### 最小可用模式

如果只想生成菜谱方案（不做完整审核流程），可以：

1. 运行 `recipe_preflight.py` 获取数据
2. 按 SOP 生成方案
3. 运行 `recipe_review_gate.py` 做基础规则检查
4. 手动检查 `references/quality-checklist.md`
5. 用户确认后运行 `record_plan.py`
6. 饭后运行 `record_feedback.py`

### 完整审核模式

需要能够并行启动 3 个审核 agent 的环境（Codex subagent、或手动启动 3 个独立 session）。
`review_pipeline.py` 可作为本地编排入口：先跑自动审核门，待 3 个审核 JSON 准备好后再聚合裁决。

## 版本历史

- **v4.1** — Feedback 闭环 / SOP 2.0 cron 模板 / 主材泛化 fallback
- **v4.0** — 补齐全部审核基础设施（2个脚本 + 3个模板 + 5个参考文档）
- **v3.4** — 预检脚本创建 + 同套主材撞车修复
- **v3.3** — MAIN_INGREDIENT_MAP 变体覆盖 + 汤锅复用规则
- **v3.0** — 工程化升级（预检脚本硬拦截 + 自动审核门）
- **v2.0** — 三 subagent 并行对抗架构
- **v1.x** — 单一 subagent 审核

## License

Personal use. Derived from Hermes Agent skill system.
