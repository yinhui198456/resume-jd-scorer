---
name: weekend-lunch-plan
description: 当用户说“周末午餐建议”、“周末早餐建议”、“早餐建议”、询问周末吃什么、早饭/早餐吃什么、午餐方案、家庭备餐计划、提供现有食材、确认菜单或饭后反馈时使用。支持健康周末午餐与早餐推荐，并按 SOP 执行数据预检、自动审核门、3 subagent 模板审核、聚合裁决、历史记录和反馈闭环。
version: "4.1-codex"
base_skill: "weekend-lunch-plan v4.1"
merged_skills:
  - "recipe-food-safety"
  - "recipe-sop-discipline"
---
# weekend-lunch-plan (Codex 适配版)

> 本文件合并了 `weekend-lunch-plan` + `recipe-food-safety` + `recipe-sop-discipline` 三个 skill 的内容，适配 Codex / 独立 Agent 环境使用。

---

## 支持文件速查

### Scripts（可直接运行）
- `scripts/recipe_preflight.py` — SOP 1 数据预检（黑名单/库存/意向池/feedback）
- `scripts/recipe_review_gate.py` — SOP 1.5 自动审核门（10项纯规则检查，stdin 输入）
- `scripts/recipe_eval_aggregator.py` — SOP 1.5 聚合裁决（PASS/FAIL/FALLBACK）
- `scripts/review_pipeline.py` — 本地审核流水线（审核门 + 三方评估聚合）
- `scripts/record_plan.py` — 用户确认方案后写入 `history.json`
- `scripts/record_feedback.py` — 饭后写入 `dish_feedback.json`
- `scripts/feedback_reminder.py` — 输出近期待反馈菜品

### Templates（subagent prompt 模板）
- `templates/eval-validator.md` — 校验官（9项检查：结构/排重/黑名单/口味/热门/当季创意）
- `templates/eval-chef.md` — 厨师（8项检查：时间/器具/人力/并行/烹饪常识/食品安全）
- `templates/eval-redteam.md` — 红队（10项检查：成分/类别/创意真实性/去重/定位）
- `templates/eval-breakfast-validator.md` — 早餐校验官（结构/时间/营养/低油低糖/儿童友好/食品安全）
- `templates/feedback-cron.example` — 反馈提醒 cron 示例

### References（参考文档）
- `references/popular-dishes.md` — 热门菜品验证表（7月时令+全年常备）
- `references/dish-technique-notes.md` — 详细做法参考
- `references/quality-checklist.md` — 主 agent 自检前置清单（16节）
- `references/breakfast-checklist.md` — 早餐质量清单（meal_type=breakfast 专用）
- `references/cooking-research-notes.md` — 烹饪研究笔记（网友教训汇总）
- `references/chef-review-cases.md` — 厨师审核实战案例（6个案例）
- `references/consistency-audit.md` — 一致性审计日志
- `references/session-2026-06-15-review.md` — 历史复盘记录
- `references/lark-cli-pitfalls.md` — 飞书CLI陷阱（归档，Codex环境可选）
- `references/culinary-craft-review.md` — 烹饪工艺审核要点
- `references/audit-case-2026-06-06.md` — 红队审计实战案例

**⚠️ 维护纪律**：新增 SOP 步骤时，必须同步创建对应的 script/template 文件。

## 触发场景
用户询问周末吃什么、午餐方案、早餐建议、早饭吃什么、备餐计划、提供现有食材、确认菜单、或表达想吃某道菜。

## 餐次模式

默认餐次：

```text
meal_type = lunch
```

当用户明确说“早餐建议 / 周末早餐 / 早饭吃什么”时：

```text
meal_type = breakfast
```

历史记录必须写入 `meal_type`。旧记录缺少 `meal_type` 时按 `lunch` 兼容处理，避免早餐和午餐排重互相污染。

## 核心约束
- **健康基线**：中度脂肪肝（低油低糖）、儿童高钙/高锌/高蛋白。
- **菜品结构**：**2 大荤 + 1 素/小荤 + 1 汤 + 1 主食**（3菜1汤+主食。主食必须明确列入方案，以便器具冲突检查。第三道菜允许是纯素或荤素搭配的小荤）
  - **【素】定义**：0 荤料（蛋=荤，皮蛋=蛋=荤，含蛋不能标素）。必须核查配料表验证。
  - **【小荤】定义**：含肉/蛋但蔬菜占比 ≥50%，肉/蛋占比 <30%。无肉无蛋的必须标【素】。
- **口味偏好**：
  - 菜系：**江浙、广东、潮汕、闽菜、鲁菜清淡款、川菜不辣款、湘菜不辣款、西式简餐、日式**（清淡、鲜香、原汁原味）
  - **几乎不吃辣**（藤椒、花椒、辣椒、红油、辣子、小炒等含辣含麻类全部排除。川菜/湘菜必须用不辣改良版）
  - **不喜甜**（菠萝排骨等甜口菜排除，糖醋/红烧类需标注少糖版。西式菜品注意控制糖分）
- **用户烹饪熟练度：新手/不熟练**
  - 推荐优先选择**刀工简单**（切块/切丝/切片即可，无花刀要求）、**调味单纯**（基础酱油/盐/料酒，无复杂酱汁调配）、**火候要求宽松**（大火快炒/定时烤箱/一键电压锅，无需精准控温）的菜品
  - 排除：花刀（如鱚鱼打花刀/麦穗花刀）、分餐摆盘复杂、需精准温控的分子料理或低温慢煮、需分次调味且时机要求严苛的菜
  - 优先：腌制类（一腌就走）、电压锅/烤箱类（放进去可离开）、空气炸锅快手菜
- **方案要求（每套必须同时满足）**：
  - 至少 **1 份创意菜**（符合以下任一：① 网红改良款如蒜蓉粉丝蒸鲈鱼/盐葱鸡腿肉；② 有仪式感的摆盘菜；③ 新派做法如空气炸锅版、电饭煲懒人版。普通家常菜如蛤蜊蒸蛋、清炒时蔬不算）
  - 至少 **1 份当季菜**（时令食材/应季做法）
  - 总体制作时间 **≤ 45 分钟**
  - 工艺不能太复杂（排除需长时间炖煮/多道工序/专业设备的菜）
- **特色度要求**：每套方案至少 1 道菜需有"餐厅感"——食材组合讲究、烹饪手法多样、菜名有记忆点、或上桌有仪式感（热油激香/揭盖蒸汽等）。详见 `references/quality-checklist.md §16`。
- **做菜教训**：四季豆/春笋必须焯水；菌菇汤每周≤1 次；清蒸必须活鱼；禁止写"清炒时蔬"。
- **做法/配搭去重**：同一"主食材+核心做法前缀"30天内不重复。详见 quality-checklist.md §7c。
- **季节性温燥**：5月-9月（盛夏）排除羊肉、狗肉、鹿肉等温燥食材。换清爽海鲜/禽类。
- **当日食材撞车**：同天已吃的主食材不再出现在下一餐推荐。
- **永久排除菜品**：苦瓜（用户明确不爱吃，所有含苦瓜的菜品排除）。
- **用户偏好：红烧/浓油赤酱类菜品默认预留青红椒点缀位**（青甜椒+红甜椒各半个，切菱形块，收汁前2分钟下锅翻匀断生，提色不抢味）。
- **菜品来源标准**：推荐的菜品必须是真实存在的热门菜品。禁止杜撰不存在的菜名、禁止用「食材A+食材B」式机械组合命名。优先选择有明确菜谱流传、社区验证过的经典/网红菜。
  - 优先查阅 `references/popular-dishes.md` 热门菜品参考表（已标注验证日期和多平台来源）
  - 表内标记 ✅ 的菜品为已验证热门，直接通过
  - 参考表没有的候选菜，通过浏览器访问下厨房/美食天下/豆果等平台验证
  - 无法验证的冷门组合直接淘汰，换经典款

## 早餐模式约束

早餐推荐使用轻量结构，不套用午餐的“大荤/汤/创意菜”要求。

早餐生成和审核必须参考 `references/breakfast-checklist.md`。

每套早餐必须包含：

- **1 主食**：蛋饼、饭团、馄饨、贝果、杂粮粥、蒸点等
- **1 蛋白**：鸡蛋、虾仁、鸡胸、奶酪、酸奶等
- **1 饮品**：牛奶、无糖豆浆、玉米汁、米糊等
- **1 果蔬**：小番茄、黄瓜条、蓝莓、香蕉、时令水果等

早餐质量要求：

- 总体制作时间建议 ≤ 20-30 分钟
- 低油、低糖、少油烟
- 儿童友好，兼顾高蛋白、高钙
- 优先使用豆浆机、电蒸锅、电饭煲、空气炸锅等可离开器具
- 允许前一晚预处理
- 不要求“餐厅感”和复杂摆盘

早餐审核流程：

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/recipe_review_gate.py --meal-type breakfast --input plan.json
```

自动审核门通过后，使用 `templates/eval-breakfast-validator.md` 做早餐专项审核。早餐不强制启动午餐三方审核模板，除非方案里包含复杂烹饪或高风险食材。

## 🍳 厨房器具清单

**自动器具（放进去可离开，优先并行）：**
- **电压锅**：炖肉、排骨、蹄筋等硬菜（上汽后需人工泄压）
- **电蒸锅**：蒸鱼、蒸粗粮、蒸点心（上汽快，可多层）
- **电饭煲**：煮饭、煮粥。**⚠️ 注意**：如果方案中有"电饭煲版"菜品（如电饭煲豉油鸡），与煮饭互斥，只能二选一或错峰制作。
- **空气炸锅**：烤肉、炸鸡、复热（免油烟）
- **微波炉**：热菜、蒸蛋、解冻
- **豆浆机**：玉米汁、米糊、豆浆（需提前备料，运作期间可离开，全自动）

**人工器具（需全程盯守，不可并行）：**
- **炒锅**：炒菜、红烧、焯水
- **煎锅**：煎牛排、煎饺
- **汤锅**：煮汤（煮沸后可转小火离开）

---

## 数据文件定义

| 文件 | 路径 | 用途 |
|---|---|---|
| **history.json** | `data/history.json` 或自定义路径 | 30 天已做菜品（排重黑名单） |
| **inventory.json** | `data/inventory.json` | 冰箱存量食材（优先消耗） |
| **wishlist.json** | `data/wishlist.json` | 意向菜品池（推荐优先） |
| **dish_feedback.json** | `data/dish_feedback.json` | 菜品使用反馈 |

**⚠️ 文件不存在时**：创建空数组 `[]`，禁止跳过。

---

## SOP 1：方案生成前（Load & Exclude） **[HARD GATE]**

**禁止手动读取 JSON + 口述数据汇总。必须先运行预检脚本，用其输出作为数据源。**

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/recipe_preflight.py
```

脚本自动完成：
1. 读取 history.json → 清洗未来日期 → 构建排重黑名单（菜名归一化 + 主食材黑名单）
2. 读取 inventory.json → 自动标记过期食材 → 写回更新后的文件
3. 读取 wishlist.json → 提取意向池
4. 读取 dish_feedback.json → 提取 disliked/loved 列表
5. 生成建议采购清单（基于主材 + 当季补充）
6. 输出 JSON 格式的预检报告

**主 agent 解析脚本输出的 JSON 报告，用其中的黑名单和可用食材列表构建候选池。禁止跳过脚本手动操作。**

### 手动补充步骤（脚本完成后）
1. **候选池提取**：从 wishlist + 库存匹配菜 + 当季时令菜提取候选池
2. **热门验证（强制）**：候选菜品先在 `references/popular-dishes.md` 中查找，标记 ✅ 的菜品直接通过。表外菜品通过浏览器访问下厨房/美食天下/豆果等平台验证
3. **库存标注**：每道菜必须标注【匹配库存：xxx】或【无匹配，需采购】

---

## SOP 1.5：方案审核（三 Subagent 并行对抗审查） **[MANDATORY]**

### 审核流程

```
主 agent 生成 3 套初稿方案
  │
  ├── 第一步：自动审核门 recipe_review_gate.py（纯规则检查，硬拦截）
  │   └── 结构/主料撞车/辣味/苦瓜/素菜纯度/时间/库存标注/当季创意/30天排重
  │       → FAIL = 自动驳回，主 agent 修正后重跑
  │
  ├── 第二步：主 agent 自检前置（按 quality-checklist.md 快速扫一遍）
  │
  ├── 启动 3 个并行审核 subagent ─────────────┐
  │   ├── 校验官 (templates/eval-validator.md) │
  │   ├── 厨师   (templates/eval-chef.md)     ├── 并行审核
  │   └── 红队   (templates/eval-redteam.md)  │
  │                                           │
  ▼                                           ▼
recipe_eval_aggregator.py 聚合裁决
  ├── 全部 ✅ → 展示给用户
  └── 任一 ❌ → 修正全部不合格项，重新跑审核（最多 3 次）
```

1. **第一步：运行自动审核门** — 纯规则检查（不依赖 LLM），返回 FAIL 则自动驳回
2. **第二步：主 agent 自检** — 按 `references/quality-checklist.md` 快速扫一遍
3. **并行调用 3 个审核 subagent**，每个加载对应模板文件作为完整 prompt
4. 3 个结果通过 `scripts/recipe_eval_aggregator.py` 聚合裁决

本地编排可使用：

```bash
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/review_pipeline.py
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/review_pipeline.py --evals evals.json
```

**⚠️ 强制规则**：
- 主料撞车/同类做法撞车/辣味上菜/苦瓜 = 一票否决
- 边界情况从严，不确定默认 ❌
- **禁止在任一 subagent 未通过时向用户输出方案**

### 降级回退
- 3 个中有 2+ 个 subagent 失败 → 主 agent 自行按 quality-checklist.md 全量审核
- 全部失败 → 标记「⚠️ 审核不可用」，主 agent 自行审核后展示

---

## SOP 2：方案确认后（Write & Update）

### 2.1 更新 history.json
用户确认某套方案后，运行：

```bash
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/record_plan.py --selected 方案A --meal-type lunch
cat plan.json | RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/record_plan.py --selected 方案A --meal-type breakfast
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/record_plan.py --input plan.json --selected 方案A --meal-type breakfast
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/record_plan.py --meal-type breakfast --input plan.json --selected 方案A
```

该脚本按日期 upsert `history.json`，避免同一天重复记录。

### 2.2 更新 wishlist.json
新增意向菜品时查重后追加。

### 2.3 更新 inventory.json
根据本次菜单推断已消耗的食材，标记为 used。

---

## SOP 3：存量食材录入（Inventory Management）

用户报食材时，读取 inventory.json，新增/更新食材，清理过期条目。

### 保质期参考
- 叶菜类：2-3 天 | 根茎类：5-7 天 | 肉类（冷藏）：2-3 天 | 蛋类：7-14 天 | 海鲜：1 天

---

## SOP 4：查询当前食材

按 expire_date 升序排列，标注临期（≤2 天）食材，建议优先消耗项。

---

## SOP 5：意向菜品录入（Wishlist Input）

用户表达想吃某道菜时，查重后追加到 wishlist.json。优先级根据用户语气判断（"特别想吃"→high / "随便加"→low / 默认→medium）。

---

## SOP 6：菜品使用后反馈记录（Dish Feedback）

用户反馈菜品后，写入 dish_feedback.json。rating 映射：
- love：好吃/太棒了/下次还做/孩子爱吃
- neutral：还行/不错/可以/一般般/没感觉/就那样
- dislike：不好吃/太膻/太淡/太腻/不要再做/孩子不吃

记录命令：

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/record_feedback.py --dish 菜名 --rating love --note "可选备注"
```

查看近期待反馈菜品：

```bash
RECIPE_DATA_DIR=<DATA_DIR> python3 scripts/feedback_reminder.py --days 7
```

如需外部定时提醒，参考 `templates/feedback-cron.example`。飞书归档仍为可选发布目标，使用前先按 `references/lark-cli-pitfalls.md` 验证 `lark-cli` 环境。

**候选池过滤**：dislike 评级菜品 60 天内不推荐，love 评级提高权重。

---

## 🔬 食品安全审核清单（来自 recipe-food-safety）

> 厨师审核 subagent 必须逐项检查以下规则。

### P0：食品安全（一票否决）

**S1 海鲜中心温度**
- 鲜贝/虾/贝类需中心温度≥60°C/1分钟（副溶血性弧菌）或≥85°C/1分钟（诺如病毒）
- **焯水30秒不足** → 最低标准：焯水≥1分钟，或标注视觉判断「从半透明变为乳白色且边缘微卷」

**S2 焯水换水纪律**
- 猪肉/重味食材焯水后，不可直接用同一锅水焯海鲜/轻味食材
- 正确做法：倒掉脏水→冲洗锅→重新烧清水，或先焯海鲜后焯猪肉

**S3 猪肉/禽类处理**
- 猪肉焯水必须冷水下锅，大火煮开后撇去浮沫，时间≥3分钟
- 禽类需确保内部无粉红色，汁水清澈

**S4 豆腐蛋液煎熟**
- 热锅中火，豆腐厚度≤1cm，每面煎3-4分钟至蛋液完全凝固
- 焖塌5分钟（90-95°C）确保蛋液完全熟透

### P0：时间线审核（一票否决）

**T1 高压锅完整链路**：上汽(5-10min) + 压制 + 泄压(3-5min) + 收汁(2-3min)
**T2 烤箱/空气炸锅预热**：烤箱5分钟，空气炸锅2-3分钟
**T3 换锅串行时间**：共用人工器具必须串行，换锅需计入1-2分钟洗锅时间

### P1：调料量化

| 模糊表述 | 应替换为 |
|---------|---------|
| "适量油" | "2汤匙（约30ml）" |
| "少许盐" | "半小勺（约2g）" |

### 健康约束（脂肪肝/低油低糖）
- 单菜用油 ≤ 1.5汤匙（约20ml）
- 全餐总油量 ≤ 2-3汤匙（约30-45ml）
- 糖控制在1/4小勺以内

---

## 🛡️ SOP 执行纪律（来自 recipe-sop-discipline）

### 铁律：少一步 = 不合格

```
1. 预检脚本 → 获取黑名单/库存/意向池
2. 候选池提取 + 热门验证
3. 生成3套初稿方案
4. 自动审核门 → 纯规则检查，FAIL则驳回
5. 主 agent 自检
6. 3 subagent 并行审核
7. 聚合裁决 → 全部通过才交付
```

**不得在任一审核未通过时向用户输出方案。**
**宁可多花时间跑完SOP流程，也不要快速交付半成品。质量>速度。**

### 常见陷阱

| 陷阱 | 描述 | 解决 |
|------|------|------|
| 创意菜标签滥用 | 普通煎/烧/炒硬贴创意标签 | 红队一票否决 |
| 同套餐做法重复 | 两道大荤相同核心技法 | 红队一票否决 |
| 汤锅串行过多 | 汤锅使用>2道 | 厨师否决，分配到不同器具 |
| 鸡蛋频次超限 | 3套方案中鸡蛋>2次 | 跨方案去重 |
| 审核基础设施空壳 | 脚本/模板缺失导致审核跳过 | 运行前验证文件存在性 |

---

## ⚠️ 重要陷阱与维护规则

### 汤锅复用冲突（P0）
方案同时有"汤锅类汤品"+"需要汤锅焯水/白灼的菜" → 必须写明：汤炖好后转移到砂锅/保温容器，释放汤锅。

### MAIN_INGREDIENT_MAP 烹饪方法变体覆盖
任何"烹饪方法+主材"格式（烧X/炒X/烤X/炖X/蒸X/煎X）都需要被映射到主食材。发现漏掉的归一化条目立即补到脚本的 MAIN_INGREDIENT_MAP。

### 同套方案内主材撞车（P0）
同一套方案内，每道菜的主食材（归一化后）必须互不相同。主食不参与主材去重。

### 审核基础设施缺失时的纪律
1. **预检脚本必须实际运行**，禁止口头汇总 JSON 数据替代
2. **运行前必须验证基础设施存在性**
3. **任一审核组件缺失时，禁止向用户输出方案**

### Python 脚本 import 铁律
所有 import 必须在文件顶部（模块级），禁止在函数内局部 import。

### 时间表设计陷阱
- 泡发/腌制/解冻 >10分钟的操作必须标注为「第零步：提前准备」
- 自动器具启动必须错峰（间隔2-3分钟）
- 时间表写完后逐道对照烹饪步骤验证

---

## 输出结构（用户确认前）

### 第一步：需求总结
家庭成员/健康/口味/当季/库存匹配/排除项

### 第二步：3 套完整方案（每套必须有独立主题）
- **方案A**：🌿 当季主打
- **方案B**：💡 创意/人气
- **方案C**：🏠 经典家常

每套方案格式（**禁止表格，纯文本列表**）：
```
🍽️ [主题名]
【大荤】菜名 — 匹配库存：xxx — 当季标签：xxx — 推荐理由 — 预估时间：x分钟
【大荤】菜名 — 匹配库存：xxx — 当季标签：xxx — 推荐理由 — 预估时间：x分钟
【素/小荤】菜名 — 匹配库存：xxx — 当季标签：xxx — 推荐理由 — 预估时间：x分钟
【汤】菜名 — 匹配库存：xxx — 当季标签：xxx — 推荐理由 — 预估时间：x分钟
【主食】从 popular-dishes.md 主食类中选择 — 制作方式：xxx — 预估时间：x分钟
⏱️ 预计总制作时间：xx分钟（≤45分钟）
```

### 第三步：三套对比简述
一句话对比三套方案的适用场景

### 用户确认后：完整操作流程文档
- 菜单总览、食材清单（主材精确到克，调料用直观单位）、第零步提前准备、烹饪步骤详解
- 步骤采用「一道一道菜」顺序，禁止使用 [T+X min] 并行时间线格式
- 写入前启动厨师审核 subagent 审核
- **飞书 bot 对话回传**：如果当前请求来自飞书/Lark bot 对话（例如上下文标明 Feishu/Lark、用户提到“飞书bot”、或会话由飞书桥接进入），生成操作指南后必须把完整做菜操作步骤正文发送到当前对话；不要只回复本地文件路径。若正文过长，先发送菜单总览、采购清单、第零步和逐道步骤的精简版，再补充文件路径作为归档。
- **对话内排版**：发送到当前对话的大段步骤必须做轻量排版，便于手机查看：按「菜单 / 第零步 / 第1道菜 / 第2道菜 / 上桌顺序 / 关键提醒」分块；块之间留空行；每块控制在 3-7 条短句；优先使用编号列表，避免长段落和大表格。飞书场景下必要时分多条消息发送。

---

## 数据结构校验

每次写入 JSON 前，确保：
- JSON 格式合法（可被 `json.loads` 解析）
- `history.json` 条目数合理（≤ 30 条，每日 1 条）
- `wishlist.json` 无重复 `name`
- `inventory.json` 过期条目已标记
