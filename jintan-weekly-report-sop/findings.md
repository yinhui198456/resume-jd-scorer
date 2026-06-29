# 发现与决策 — 金坛二期周报 loop engineering

## 需求
通过 loop engineering 方法持续完善金坛二期周报生成流程，覆盖数据 freshness、版式、校验、模板、自动化和 LLM 下周计划推断 6 个方向。

## 研究发现

### 当前流程稳定性
- `report_pipeline.py` 已集成 flock 锁、生成、结构校验、话术校验和自动修复循环
- 退出码定义清晰：0 通过、1 错误、2 需人工审查
- 自动修复覆盖：空编号、eastAsia、模糊用语、Markdown、占位符
- 人工审查触发：gridSpan、vMerge、重复内容、页面1、首页留白、合并单元格

### 数据源现状
- 本地 xlsx：`data/金坛二期项目跟进表.xlsx`，2026-06-28 17:47 版本
- 在线文档：腾讯文档，通过 `fetch-jintan-data.py` 拉取
- 实际使用 3 个 Sheet：01-项目计划、02-项目里程碑、04-应用问题跟踪表

### 下周计划推断问题
- 在线文档没有专门的"下周计划"列
- 当前 `report_engine_v9.py` 通过规则推断：未完成任务 + 计划开始时间 <= 下周五
- 规则推断存在局限：无法从备注/状态理解任务真实意图，可能遗漏应继续推进的任务，或包含不应列入的任务
- 引入 LLM 可以从自然语言备注中提取下周行动意图，但需要：
  - 明确的 prompt 和输出 schema
  - 严格的成本控制（只处理少量候选任务）
  - 可解释的 fallback 到现有规则
  - 完整的单元测试覆盖

## 技术决策
| 决策 | 理由 |
|------|------|
| 先刷新数据 | 确保后续优化基于最新数据 |
| LLM 下周计划默认禁用、可配置启用 | 避免无意的 API 调用和费用，保持现有流程稳定 |
| LLM 失败时自动回退到规则引擎 | 保证周报生成不依赖外部 LLM 可用性 |
| 模板美化本轮跳过 | PDF 复核无明显问题，避免无意义改动 |
| 自动化使用 systemd timer | 与现有 Linux 环境集成，轻量可控 |
| 每轮 loop 必须验证 | 防止优化引入回归 |

## 资源
- 项目目录：`/opt/personal-agent-workspace/jintan-weekly-report-sop/`
- Pipeline：`scripts/report_pipeline.py`
- 数据拉取：`scripts/fetch-jintan-data.py`
- 主引擎：`scripts/report_engine_v9.py`
- 校验脚本：`scripts/validate_weekly_report.py`、`scripts/validate_report_tone.py`
