# 技能一致性审计日志

## 2026-06-18 审计报告（v3.4 修复）

**触发**：预检脚本 recipe_preflight.py 自 v3.0 起就标注为硬拦截但从未创建成功（日志反复 404）+ 方案 A 同套内主材撞车（响油鳝丝+毛豆烧黄鳝）

### 发现的问题

| 项目 | SKILL.md 描述 | 实际执行 | 状态 |
|---|---|---|---|
| recipe_preflight.py 脚本 | SOP 1 硬拦截强制运行 | 脚本从未存在于 scripts/ 目录 | **已修复**：首次创建完整脚本 |
| 同套方案内主材去重 | 30 天跨套去重有，同套内无 | 方案 A 两道黄鳝菜 | **已修复**：新增同套主材撞车陷阱 |
| 方案审核 | 三 subagent + 审核门 | 预检脚本缺失导致全部跳过 | 脚本补齐后审核链可跑通 |

### 修复动作
- 创建 `scripts/recipe_preflight.py`：完整预检脚本，覆盖 history.json 清洗、inventory.json 过期标记、MAIN_INGREDIENT_MAP 归一化、wishlist 加载、JSON 报告输出
- SKILL.md：新增「同套方案内主材撞车」陷阱（P0 级）
- SKILL.md description：v3.3 → v3.4

### 根因分析
recipe_preflight.py 在 v3.0 升级时被写入 SKILL.md 作为硬拦截，但脚本创建步骤在后续 session 中可能因路径错误/写入失败而遗漏，SKILL.md 却已经引用它。此后每次运行都 404，主 agent 默默 fallback 到手动读 JSON，从未有人注意到脚本从未存在过。教训：SKILL.md 中引用 scripts/ 下文件时，创建 skill 版本必须同步验证文件存在。

---

## 2026-06-15 审计报告（v3.3 升级）

**触发**：用户发现"昨天吃过鸡了，怎么今天还在推荐？" + 厨师 subagent 发现汤锅冲突

### 发现的问题

| 项目 | SKILL.md 描述 | 实际执行 | 状态 |
|---|---|---|---|
| 主材归一化覆盖 | 仅覆盖具体菜名 | "烧鸡"等烹饪方法变体漏掉 | 已修复：MAIN_INGREDIENT_MAP 补"烧鸡/炒鸡/烤鸡/炖鸡" |
| 汤锅复用检查 | 未提及 | 器具分布合并写"电压锅/汤锅"掩盖冲突 | 已修复：新增汤锅复用冲突陷阱 + 规则 |
| lark-cli 创建文档 | v1 方式 `--title --markdown -` | v1 接口已关闭 | 已修复：改用 v2 `--api-version v2 --doc-format markdown --content` |

### 修复动作
- recipe_preflight.py：MAIN_INGREDIENT_MAP 补"烧鸡/炒鸡/烤鸡/炖鸡" → "鸡肉"
- SKILL.md：新增"汤锅复用冲突"和"MAIN_INGREDIENT_MAP 烹饪方法变体覆盖"两个陷阱
- SKILL.md：更新飞书文档创建命令为 v2 格式
- 新增 references/session-2026-06-15-review.md
- 更新 SKILL.md description：v3.2 → v3.3

### 根因分析
MAIN_INGREDIENT_MAP 采用具体菜名映射，没有覆盖"烹饪方法+主材"的通用模式。
器具分布表的合并写法掩盖了真实的器具占用。

---

## 2026-05-31 审计报告（v3.0 工程化升级）

**触发**：用户发现主 agent 跳过 SOP 1 热门验证 + SOP 1.5 三 subagent 审核 + 库存过期清理未实际执行

### 发现的问题

| 项目 | SKILL.md 文本 | 实际执行 | 状态 |
|---|---|---|---|
| SOP 1 数据准备 | 手动 read_file + 口述汇总 | 跳过/只说不做 | 已修复：recipe_preflight.py 硬拦截 |
| SOP 1 热门验证 | 强制不可跳过 | 只对1道菜标注验证 | 已修复：preflight 加载 verified_dishes |
| SOP 1.5 三 subagent 审核 | MANDATORY | 完全没跑 | 已修复：recipe_review_gate.py 自动审核门前置 |
| 库存过期清理 | 标记 expired 并 write_file | 口头说了没写 | 已修复：preflight 自动标记+写回 |

### 修复动作
- 新增 `scripts/recipe_preflight.py`：SOP 1 数据准备工程化（自动清洗 JSON + 构建黑名单 + 标记过期 + 输出预检报告）
- 新增 `scripts/recipe_review_gate.py`：SOP 1.5 自动审核门（纯规则检查 10 项，FAIL 则自动驳回）
- 更新 SKILL.md description：v2.0 → v3.0
- 更新 SKILL.md SOP 1：改为 [HARD GATE]，强制运行预检脚本，禁止手动读 JSON
- 更新 SKILL.md SOP 1.5：审核流程新增"第一步：自动审核门"，在 subagent 之前拦截机械错误
- 记录本次教训到 SKILL.md 陷阱区

### 根因分析
SOP 约束全在 prompt 文本里，没有代码层面的强制。主 agent 可以靠"自律"执行，但遇到上下文压力时优先跳过最费时的步骤。修复思路：把"靠自觉"变成"脚本不跑完就卡住"。

---

## 2026-05-24 审计报告

**触发**：用户发现流程图缺失「热门菜品验证」步骤

### 发现的问题

| 项目 | SKILL.md 文本 | diagrams/ 流程图 | 状态 |
|---|---|---|---|
| 热门菜品验证 (SOP 1 §5) | ✅ 有 | ❌ 缺失 | 已修复 v3.0 |
| 候选池提取 | ✅ 有 | ❌ 缺失 | 已修复 v3.0 |
| 库存匹配标注 | ✅ 有 | ❌ 缺失 | 已修复 v3.0 |
| 主料黑名单+菜名归一化 | ✅ 有 | ⚠️ 过于简化 | 已修复 v3.0 |
| 三 subagent 审核 | ✅ 有 | ✅ 有 | 同步 |
| 聚合裁决脚本 | ✅ 有 | ✅ 有 | 同步 |
| 飞书文档保存 (SOP 2.4) | ✅ 有 | ⚠️ 旧版未标注 | 已修复 v3.0 |

### 修复动作
- 重写 `diagrams/weekend-lunch-plan-sop.drawio`（v2.0 → v3.0）
- 重新导出 `diagrams/weekend-lunch-plan-sop.png`
- SKILL.md 新增「流程图与 SKILL.md 文本脱节」陷阱记录
- SKILL.md 新增「库存匹配纪律」陷阱记录
- 清理 workspace 临时文件

### 根因分析
流程图作为独立 artifacts 维护，SKILL.md 文本升级时没有同步更新 drawio 文件。
用户追问"怎么这个步骤没了"才暴露。

### 未来审计建议
每次 SKILL.md 大版本升级后，对比 drawio 文件节点数与 SOP 步骤数，确保 1:1 对应。

## 2026-05-24 第二轮审计（技能库维护）

**触发**：session review 发现 xhs CLI 批量查询问题和 inventory.json 过期清理缺失

### 发现的问题

| 项目 | SKILL.md 描述 | 实际执行 | 状态 |
|---|---|---|---|
| xhs CLI 批量查询 | "部分关键词返回空" | 9/9 全部返回空，批量查询几乎必崩 | 已修补 xhs CLI 已知问题 |
| inventory.json 过期清理 | SOP 1 §3 只筛选不清理 | 13 条过期食材仍标 available | 已修补 SOP 1 §3 增加自动清理 |
| xhs 降级策略 | "连续失败降级" | 应边跑边判断，不应等全部跑完 | 已修补应对策略 |

### 修补动作
- SKILL.md xhs CLI 已知问题区：增加"批量查询风控"教训 + "边跑边判断"策略
- SKILL.md SOP 1 §3：增加自动清理过期条目规则
