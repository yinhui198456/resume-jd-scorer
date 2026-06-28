# Findings & Decisions

## Requirements
用户要求使用 Planning with Files 为"修复上述问题"建立轻量开发计划。修复范围覆盖 `jintan-weekly-report-sop` 中文档、配置与脚本的不一致和缺陷。

## Research Findings
- 项目目录结构完整，`SKILL.md` v12.2 与实际代码存在描述偏差
- `DEPLOYMENT.md` 声称核心引擎缺失，但 `report_engine_v9.py` 和 `validate_weekly_report.py` 已存在
- 实际数据源仅 3 个 Sheet，而 `SKILL.md` 描述为 6 个 Sheet
- 最新已生成周报：`20260622-0626`，邮件正文显示任务统计与引擎输出一致

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 优先修复配置/代码不一致 | 低风险、高收益，能立即提升流程稳定性 |
| 保持 `report_engine_v9.py` 主体逻辑不变 | 避免引入回归，仅修复已定位的打印和边界问题 |
| `generate-milestone-image.py` 改为从 `config.yaml` 读取关键参数 | 消除硬编码与配置漂移 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `DEPLOYMENT.md` 描述与目录实际状态不符 | 计划更新文档，移除过时断言 |
| `report_engine_v9.py` 控制台打印行数为 0 | 计划修复键名使用 |
| Row 5/Row 6 标题重复 | 计划清理冗余写入 |
| `clean_notes()` 本周范围不一致 | 计划统一为周一至周日 |
| `generate-milestone-image.py` 参数硬编码 | 计划改为读取 `config.yaml` |
| `validate_report_tone.py` 风险正则依赖已清除占位文字 | 计划调整正则或检查逻辑 |

## Resources
- 项目目录：`/opt/personal-agent-workspace/jintan-weekly-report-sop/`
- 配置文件：`config.yaml`
- 主引擎：`scripts/report_engine_v9.py`
- 校验脚本：`scripts/validate_weekly_report.py`、`scripts/validate_report_tone.py`
- 图片生成：`scripts/generate-milestone-image.py`

## Visual/Browser Findings
- 暂无视觉/浏览器内容
