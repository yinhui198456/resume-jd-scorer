# Task Plan: 修复金坛二期周报 SOP 已知问题

## Goal
修复 `jintan-weekly-report-sop` 中文档、配置与脚本的不一致及已知缺陷，使完整生成流程（拉取数据 → 生成图片 → 生成周报 → QA/话术校验）可稳定运行并通过校验。

## Current Phase
Phase 2

## Phases

### Phase 1: 问题盘点与优先级确认
- [x] 检查项目目录结构与文件清单
- [x] 识别文档/配置/脚本中的不一致和潜在缺陷
- [x] 将问题记录到 `findings.md`
- **Status:** complete

### Phase 2: 文档与配置同步
- [x] 更新 `DEPLOYMENT.md`，删除"核心引擎不存在"等过时描述
- [x] 统一 `config.yaml` 与 `generate-milestone-image.py` 的硬编码参数
- [x] 核对 `fetch-online-sheet.py` 的 `SHEETS` 列数配置（列数足够覆盖实际字段，保持现状）
- **Status:** complete

### Phase 3: 引擎代码修复
- [x] 修复 `report_engine_v9.py` 主函数打印 bug（`data.get("1")` → 正确使用键名）
- [x] 清理 Row 5 与 Row 6 的重复标题写入
- [x] 统一 `clean_notes()` 的"本周"范围为周一至周日
- [x] 简化或修正下周任务 `action_suffix` 的已完成分支
- **Status:** complete

### Phase 4: 校验脚本修复
- [x] 修复 `validate_report_tone.py` 的 `check_risk_visibility()` 正则，匹配当前模板结构
- [x] 确认 `validate_weekly_report.py` 的空任务占位符检查不过激
- **Status:** complete

### Phase 5: 集成验证
- [x] 运行 `fetch-jintan-data.py` 拉取最新数据
- [x] 运行 `generate-milestone-image.py` 生成里程碑图
- [x] 运行 `report_engine_v9.py` 生成周报
- [x] 检查 `validate_weekly_report.py` 和 `validate_report_tone.py` 输出（均 PASS）
- [x] 将测试结果记录到 `progress.md`
- **Status:** complete

### Phase 6: 交付
- [x] 汇总变更文件列表
- [x] 输出 git status 摘要
- [x] 向用户报告修复结果
- **Status:** complete

## Key Questions
1. 是否需要保留旧版引擎 `jintan_report.py` / `project_report.py`？（当前建议保留，不破坏现有路径）
2. `generate-milestone-image.py` 是否应完全改为读取 `config.yaml`，还是仅同步关键参数？
3. 校验失败时是否应让引擎退出码非零？当前仅打印告警。

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 轻量修复，不重写架构 | 当前 v9 引擎已能生成可用周报，优先修复不一致和明显 bug |
| 规划文件放在项目目录 | 便于与项目代码一起被 git 跟踪 |
| 旧版脚本保留 | 避免破坏潜在依赖，仅标记为 legacy |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 暂无 | - | - |

## Notes
- 修复前先读取相关文件，避免误改
- 每次修改后优先运行脚本验证，不依赖"目测"
- 所有外部内容（如网页搜索）仅写入 `findings.md`，不混入 `task_plan.md`
