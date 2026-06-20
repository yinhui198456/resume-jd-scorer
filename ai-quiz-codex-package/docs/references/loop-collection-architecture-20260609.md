# 题库搜集 Loop 模式 — 架构与经验（2026-06-09）

## 核心理念

Peter Steinberger: "You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents."

**旧模式（已废弃）**：一次性 prompt → 搜所有源 → 编写 → 写入 → 退出
**新模式（Loop）**：脚本控制循环 → LLM 提取 → 脚本验证 → 循环 → 达标停止

## 架构

```
脚本（确定性）                    LLM（语义理解）
  │                              │
  ├─ 选源排序（评分+优先级）───────→  从源内容中提取
  ├─ 选模块（题数最少优先）───────→  阅读理解+MCQ转换
  ├─ 质量门控（11项预检查）───────→  编写干扰项
  ├─ MD5去重                    │
  ├─ Q-ID分配                   │
  ├─ 写入bank.json               │
  └─ 源评分更新（源自适应）───────┘
```

## 数据源层级

### 第 1 层：Y44 共享数据（优先）
路径: `/root/.hermes/shared/y44/`
- `y44_github` (0.95) — GitHub 面试仓库列表 → LLM 选择并 curl README
- `y44_nowcoder` (0.90) — 牛客面经索引 → LLM 找有问题的面经并提取
- `y44_cnblogs` (0.70) — 博客园文章列表 → LLM 选相关主题并提取
- **LeetCode 不集成**：算法题与 AI 八股文不相关

### 第 2 层：GitHub raw（补充）
- `github_llm_interview` (0.80) — curl 直接下载
- `github_ai_eng` (0.70) — curl 直接下载
- `github_llm_genai` (0.70) — curl 直接下载
- `github_devinterview` (0.60) — curl 直接下载

### 第 3 层：web_search（补充）
- `nowcoder` (0.90), `juejin` (0.80), `zhihu` (0.70), `csdn` (0.50)

## ⛔ 致命陷阱：禁止编造题目

**用户原话**：「这不是欺骗吗？我要的是4平台的数据，为什么是**编写**了题目？？？？」「这不是欺骗吗？」

**事故经过**：
1. Y44 索引数据只有仓库名/面经标题，没有实际内容
2. curl 仓库 README 404 后，LLM 用"专业知识"编造了 4 道题
3. 质量门控"通过"了 2 道 → 入库 → 用户发现是编造的

**铁律**：
- **绝对禁止**凭自己的知识编写/创作/编造题目
- **绝对禁止**用"专业知识"补充内容
- **只能**从实际数据源（文件内容、curl 结果、搜索结果）中提取
- 如果源内容中没有相关题目，返回空数组 `[]`
- 宁缺毋滥：0 题入库 > 编造题目入库

**脚本防护**（已实现）：
- `bank_collector.py` 的 `_generate_llm_prompt()` 三种类型（y44_local/github_raw/search）都包含 `⛔ 铁律`
- cron prompt 顶部也加了同样的铁律
- Pre-flight Quality Gate 会拦截格式不合格的题目

## 源自适应机制

`collector_state.json` 记录每个源的：
- `total_runs` — 运行次数
- `total_collected` → `total_passed` → `total_injected` — 漏斗数据
- 排序公式: `pass_rate * 0.7 + priority * 0.3`

## 脚本接口

```bash
# 启动搜集循环
python3 scripts/bank_collector.py --loop --target 35 --max-iter 10

# 从 JSON 文件导入（LLM 提取后调用）
python3 scripts/bank_collector.py --inject /tmp/extracted.json --source y44_github --module M02_Transformer

# 查看各模块题数
python3 scripts/bank_collector.py --status
```

## Cron 集成

job_id: `042e42c8a3dd`（daily-interview-bank-update-0300）
- 已改造为 Loop 模式
- LLM 在循环中负责提取，脚本负责验证/去重/入库/评分
