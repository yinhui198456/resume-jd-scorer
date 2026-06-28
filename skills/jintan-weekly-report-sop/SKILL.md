---
name: jintan-weekly-report-sop
description: 当用户提到金坛项目周报、生成周报、检查周报格式、校验周报内容、修复周报版式或 weekly report 相关任务时使用。覆盖周报生成、结构校验、版式检查和问题修复。
---

# 金坛项目周报 SOP Skill

## 重要路径

- Skill 定义：`/opt/personal-agent-workspace/skills/jintan-weekly-report-sop/SKILL.md`
- 项目目录：`/opt/personal-agent-workspace/jintan-weekly-report-sop/`
- 输出目录：`/opt/personal-agent-workspace/jintan-weekly-report-sop/output/`
- 校验脚本：`/opt/personal-agent-workspace/jintan-weekly-report-sop/scripts/`

## 触发场景

用户提到以下任一内容：
- “生成周报”、“检查周报”、“校验周报格式”
- “金坛周报”、“项目周报”
- “周报有什么问题”、“修复周报版式”
- “导出周报 PDF”、“查看周报分页”

## 工作流

1. **运行生成-校验-修复流水线**
   - 进入项目目录：`cd /opt/personal-agent-workspace/jintan-weekly-report-sop`
   - 执行：`python3 scripts/report_pipeline.py config.yaml`
   - 若输出 `human_review_needed: false` 且 exit code 为 0，可直接进入 PDF 复核
   - 若 exit code 为 2，按输出清单人工修复后重跑

2. **版式层 PDF 复核（关键）**
   - 用 LibreOffice 导出 PDF：`libreoffice --headless --convert-to pdf --outdir /tmp/jintan-report-check <docx_path>`
   - 检查项：首页无过度留白、章节标题与正文不分页断裂、无空 “一、”/“1)” 编号、表格边界正常、里程碑图可读

3. **修复与重跑**
   - 结构性问题（模板/合并单元格/固定行高）调整 `templates/` 或 `scripts/build_v2_template.py` 后重跑 pipeline
   - 内容层问题（空编号、字体缺失）pipeline 会自动修复并重新校验
   - 修复后必须再次导出 PDF 确认

## 禁止行为

- 不要直接修改历史周报文件
- 不要跳过 PDF 目视检查就声称“校验通过”
- 不要把合并单元格中的重复文本当作真实内容重复
- 不要把 pipeline 的自动修复结果当作终审，仍需人工复核 PDF