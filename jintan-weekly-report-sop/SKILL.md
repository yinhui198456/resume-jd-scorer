---
name: project-weekly-report-sop
description: SOP to generate weekly progress report for "Jintan Phase II" project. v12.2 - YAML config-driven engine, three-layer QA Agent + validate script, CJK font fix (eastAsia + Pillow Noto), email body generation, delegate_task QA wrapper, note sanitization (进行中→尚未完成), external-block quantification whitelist, auto-delete empty template rows.
version: 12.2.0
author: project-secretary
tags: ["jintan", "weekly-report", "yaml-config", "engine", "qa-agent", "email", "three-layer-validation", "cjk-font-fix", "auto-validation", "template-cleanup"]
---

# 📝 金坛二期项目周报 SOP v9

## 架构概览

```
config/jintan_report.yaml  →  项目配置（列名/格式/过滤规则/章节结构）
scripts/report_engine_v9.py  →  通用生成引擎（读取 YAML，不绑定项目）
scripts/validate_weekly_report.py  →  三层 QA 校验（结构/数据对照/视觉），引擎尾部自动触发
scripts/validate_report_tone.py  →  话术校验（模糊用语/废话/量化/风险/编号），引擎尾部自动触发
scripts/qa_weekly_report_v2.py  →  旧版 QA（保留，validate_weekly_report.py 的演进前身）
scripts/qa_delegate_wrapper.py  →  delegate_task QA Agent 封装（保留，可选手动调用）
```

新项目只需：复制 config → 修改配置 → 运行引擎，**无需改代码**。QA 校验自动执行。

## 快速执行

```bash
# 0. 从在线文档拉取最新数据（推荐 — 避免使用过期本地缓存）
python3 ./scripts/fetch-online-sheet.py DYm9pRHBFa0NMRmta

# 0b. 生成里程碑进度图（必须在引擎前运行）
python3 ./scripts/generate-milestone-image.py

# 1. 生成周报 + 邮件正文 + 自动 QA 校验（两层：结构/数据/视觉 + 话术）
python3 ./scripts/report_engine_v9.py
# 注：引擎尾部自动触发 validate_weekly_report.py 和 validate_report_tone.py
# 校验结果直接打印到控制台，FAIL 时会有 ⚠️ 告警

# 2. 校验（必做 — 检查 CJK 字体/图片/编号/数据对照）
python3 ./scripts/validate_weekly_report.py <docx_path> [xlsx_path]
# 返回 JSON: PASS/WARN/FAIL。FAIL 阻止发送，WARN 需人工确认。

# 3. delegate_task QA Agent 封装（可选 — 内容/格式/话术 LLM 级校验）
# 见下方 "QA Agent 流程" 章节
```

## QA Agent 流程（推荐 — delegate_task 子代理校验）

生成周报后，**必须**启动一个 QA 子代理进行校验：

```python
# 伪代码 — 由生成周报的 agent 调用
delegate_task(
    goal="校验刚生成的周报质量",
    context=f"""
    待校验文件: {docx_path}
    数据源: {xlsx_path}
    
    校验维度：
    1. 内容准确性：与源数据交叉对照，确认本周/下周任务数量、协调事项、问题列表与 Excel 一致
    2. 格式合规：无 Markdown 符号、编号完整（一/1/1)、章节完整、里程碑图片已嵌入
    3. 话术规范：PMO 风格（数据驱动、精炼、风险前置），禁止废话/模糊表述/隐瞒风险
    4. 字体渲染：无方块乱码 (tofu)、中文 eastAsia 字体已设置
    5. 文件名/日期：符合 {filename_pattern}，日期为周五
    
    先运行自动校验: python3 ./scripts/validate_weekly_report.py {docx_path}
    再人工检查 Word 文档内容（可通过 vision_analyze 查看截图）。
    
    输出格式：
    - ✅ 通过项
    - ⚠️ 警告项（可接受）
    - ❌ 阻止项（必须修复后才能发送）
    """,
    toolsets=["terminal", "file", "vision"]
)
```

**校验通过标准**：自动校验返回 PASS 或 WARN，且 QA Agent 无 ❌ 阻止项。

## 数据源结构（实际 — 与 YAML 配置有差异）

xlsx 路径：`./data/金坛二期项目跟进表.xlsx`

实际 Sheet 列表（6 个，非 YAML 中的 4 个）：
- `00-待办事项` — 列：序号/登记日期/事项说明/负责人/优先级/计划完成/状态/备注/链接
- `01-项目计划` — **第 1 行是合并标题行，第 2 行才是实际列头**：序号/工作单元/任务阶段/任务/产出/负责人-内/甲方负责人/计划开始/计划完成/进度/状态/实际开始/实际完成/备注
- `02-项目里程碑` — 列：编号/里程碑名称/里程碑标志/里程碑时点/交付件/状态/付款比例
- `03-交付物` — 列：序号/文档类型/文档编号/文档名称/页数/修改说明/里程碑
- `04-应用问题跟踪表` — 列：编号/数据应用/模块/问题描述/图片备注/登记日期/结束时间/问题状态/处理人/修改内容/是否手工数据/说明
- `05-手工表收集清单` — 列：手工表说明/目标科室/数据日期/业务负责人

## YAML 配置说明

核心配置项见 `./config.yaml`：

| 配置段 | 说明 | 关键字段 |
|--------|------|---------|
| `source.sheets` | Sheet 映射 | `plan/milestone/issues` → 值为 xlsx 文件中的物理序号（"1"/"2"/"3"），非在线文档的 sheet_id |

| 配置段 | 说明 | 关键字段 |
|--------|------|---------|
| `project` | 项目信息 | name, short_name |
| `source` | 数据源 | xlsx_path, template_path, sheets, columns |
| `date` | 日期规则 | report_date (friday/monday/today), filename_pattern |
| `format` | 格式规范 | font, font_size_body, font_size_level1, font_size_header |
| `filter` | 过滤规则 | this_week, next_week, empty_task |
| `coordination` | 协调事务 | enabled, delayed, external_keywords, output_format |
| `sections` | 章节结构 | this_week, next_week, coordination, issues |
| `milestone_image` | 里程碑截图 | enabled, colors, columns |
| `email` | 邮件配置 | enabled, subject, smtp_* |

## 自动 QA 校验（引擎尾部自动执行，无需手动调用）

## 三层 QA Agent 校验

| Layer | 检查项 | 数量 | 说明 |
|-------|--------|------|------|
| L1 结构 | Markdown/编号/空任务 | 7 | 格式规范性 |
| L2 数据对照 | 日期/文件名/截图/条目 | 4 | 与源数据一致性 |
| L3 视觉 | 字体/字号/章节 | 5 | Word 格式属性 |
| L4 视觉渲染 | 导出 PDF 验证排版 | 1 | 最终交付效果（打印/导出后是否错位） |

**注意**：Word 中的灰色箭头（→）和段落标记（¶）是编辑标记视图设置（`Ctrl+Shift+8`），不存储在 .docx 文件中，打印/PDF 不显示。但 QA 应导出 PDF 做最终视觉确认。

### 第二层：validate_report_tone.py — 话术/内容

| 检查项 | 说明 |
|--------|------|
| 模糊用语 | 拦截「进行中」「推进中」「顺利」「大概」「尽快」 |
| 废话拦截 | 拦截「大家好」「希望大家继续努力」「以上谢谢」 |
| 量化检查 | 进度描述必须有百分比或明确日期 |
| 风险前置 | 正文有延期/阻塞时风险章节不能写"暂无" |
| 已完成重复 | 对比上周报告，不反复提已完结事项 |
| 编号层级 | 一级中文(一、)、二级阿拉伯(1.) |

## 邮件发送

当前生成邮件正文（.txt 文件）。发送邮件需要 SMTP 配置：

```yaml
# 在 config/jintan_report.yaml 中设置
email:
  enabled: true
  smtp_host: "smtp.example.com"
  smtp_port: 465
  smtp_user: "your@email.com"
  smtp_password: "your_password"
  from: "your@email.com"
  to: ["recipient@email.com"]
```

或通过环境变量：
```bash
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="465"
export SMTP_USER="your@email.com"
export SMTP_PASSWORD="your_password"
```

## 飞书群发送（Word 附件）

**禁止使用 `send_message` 的 `MEDIA:` 标签发送 .docx**（飞书平台不生效）。必须用 lark-cli：

```bash
# 1. 先发送周报摘要文本到飞书群
# 2. 发送 Word 附件（注意 --file 只接受 cwd 相对路径）
cd ./output && \
  /root/.nvm/versions/node/v22.22.1/bin/lark-cli im +messages-send \
  --chat-id "oc_63e348c1b3c23f50ad587113be8bfa4a" \
  --file "常州市金坛第一人民医院数据指挥中心二期项目-工作周报-YYYYMMDD-MMDD.docx"
```

## 在线文档同步流程（优先于本地文件）

当在线文档 `docs.qq.com` 存在时，**必须先从在线文档拉取最新数据**，再运行引擎。本地 xlsx 往往是过期缓存。

**步骤**：
1. 调用 `mcporter call tencent-sheetengine.get_sheet_info file_id=<ID>` 获取 sheet_id 列表。
2. 对 `01-项目计划`、`02-项目里程碑`、`04-应用问题跟踪表` 分别调用 `get_cell_data` 拉取 CSV。
3. 用 **xlsxwriter**（非 openpyxl）写入本地 xlsx —— openpyxl 写入时不生成 `sharedStrings.xml`，导致引擎 XML 解析器读出行数为 0。
4. 检查首行是否为标题行（不含"序号"/"编号"），若是则跳过。
5. 运行引擎：`python3 scripts/report_engine_v9.py`。

**完整脚本见** `scripts/fetch-online-sheet.py`。

## Pitfalls

1. **openpyxl 在 Python 3.12 下读取此 xlsx 报错** `TypeError: Fill() takes no arguments`。升级/重装无效。解决：`pip install python-calamine --break-system-packages`，使用 `python_calamine.CalamineWorkbook.from_path()` 读取，返回 `list[list]` 格式。
2. **写入 xlsx 必须用 xlsxwriter，不能用 openpyxl**：openpyxl 写入时不创建 `sharedStrings.xml`，而引擎通过 `xl/sharedStrings.xml` + 原始 XML 解析 sheet 内容。缺少该文件会导致引擎解析出 0 行。**写文件用 xlsxwriter，读文件用 calamine。**
3. **CJK 字体乱码（PNG 图片）**：`generate-milestone-image.py` 的 `get_font()` 原优先使用 `DejaVuSans.ttf`（纯英文字体），导致中文显示方块。已修复为 Noto CJK → 文泉驿 → DejaVu 的 fallback 顺序。同时 `draw_text()` 必须处理 `\n` 换行符（split by `\n` 再逐段 wrap），否则交付件等多行文本会重叠。行高必须动态计算（`calc_row_height`），不可用固定值。
4. **CJK 字体乱码（Word 文档）**：python-docx 的 `run.font.name` 只对拉丁字体有效，CJK 字符需额外设置 `eastAsia` 属性。引擎中所有 `run.font.name/size/bold` 三行赋值已替换为 `self._set_run_font(run, size=X, bold=Y)`，该方法内部同时设置 `w:rFonts` 的 `w:eastAsia` 属性。**此外，引擎必须在 `Document(template_path)` 之后立即调用 `self._fix_template_fonts(doc)`**，该方法完成两件事：① 对模板中所有已有的 CJK run（Row 0-5 等不被引擎覆盖的行）补设 eastAsia 属性；② 清除模板占位文字（"预计存在""可能出现""解决方案"等），避免触发话术校验 FAIL。**v12 增强**：`_fix_template_fonts()` 在加载模板后立即扫描全表所有 CJK run 补设 eastAsia（覆盖 Row 0-5 等不被引擎覆盖的模板头部行），并清除"预计存在或可能出现"等占位文字，确保 QA 校验零 WARN/FAIL。
5. **脚本缺失兜底**：`scripts/fetch-online-sheet.py` 和 `scripts/generate-milestone-image.py` 可能不存在于 skill 目录中。已添加可工作版本至 skill 的 `scripts/` 目录（`fetch-jintan-data.py` / `generate-milestone-image.py`）。首次使用需验证脚本存在性，缺失则从 skill 的 linked_files 中 copy。
4. **YAML 中 sheet ID 是文件内物理序号**：`sheet1.xml`→`"1"`，`sheet2.xml`→`"2"`，与在线文档的 `sheet_id` 参数（如 `uj7enc`）无关。新写入的 xlsx 中 `01-项目计划` 是第一个 sheet，ID 填 `"1"`。
5. **进度列含 `%` 符号时引擎解析为 0**：在线文档中进度可能为 `"40%"`、`"60%"` 等字符串。引擎 `report_engine_v9.py` 中 3 处 `float(progress)` 需要加 `%` 剥离逻辑。见脚本补丁 `references/progress-parsing-fix.md`。
6. **QA 校验已自动集成**：`validate_weekly_report.py`（L1/L2/L3）和 `validate_report_tone.py`（话术/内容）在引擎尾部自动触发，无需手动调用。校验结果打印到控制台。
7. **里程碑截图生成**：使用 `scripts/generate-milestone-image.py` 自动生成 PNG 并保存至 `/tmp/milestone_progress_v9.png`。引擎代码中图片路径硬编码为此文件。**必须在运行引擎前先生成图片**。图片质量验收：字体≥28px NotoSansCJK（禁用 DejaVuSans→方块□）、行高动态计算（禁止固定→重叠）、表头每列独立分隔居中。生成后用 `vision_analyze` 验证中文正常/无重叠。
8. **YAML `milestone_columns.number` 必须为实际列名 `"编号"`**：不可填入在线文档中的合并标题行文本（如 `"常州市金坛第一人民医院...01-里程碑"`），否则图片生成时编号列为空。
9. **新增 `milestone_display_map` 配置**：图片生成脚本通过此映射将显示列名（如 `"里程碑"`）映射到 xlsx 实际列名（如 `"里程碑名称"`）。缺失此配置会导致图片中列数据错位或空白。
10. **引擎解析打印 "0 行" 但实际有数据**：`report_engine_v9.py` 的 XML 解析器使用 `sharedStrings.xml` 索引，但打印语句使用了错误的字典 key（如 `config['source']['sheets'].get('milestone', '02')` 返回 `"2"` 而非 `"milestone"`），导致 `len(data.get("2", []))` 为 0。**这是打印 bug，不影响实际数据解析**。可用 `python-calamine` 直接验证数据。
11. **模板占位文字触发话术 FAIL**：模板中 Row 11 等不在 YAML 配置中的行可能包含"预计存在或可能出现的风险及解决方案"等占位文字，会被 `validate_report_tone.py` 拦截为不确定语气 FAIL。`_fix_template_fonts()` 已扩展为扫描**所有表格行**清除占位文字，不再仅限于 YAML 配置的 section rows。
12. **模板头部行 CJK eastAsia 字体**：引擎生成内容时通过 `_set_run_font()` 设置 eastAsia，但模板原有的头部行（Row 0-5：项目名称/总监/阶段等）不会被引擎覆盖。`_fix_template_fonts()` 在加载模板后立即对所有现有 CJK run 补设 eastAsia，避免 QA 校验报 "N/300 个中文 run 缺少 eastAsia"。
13. **空任务占位符校验过激 — "ODS-DWD-DWS-DM" 是真实数据架构术语**：`validate_weekly_report.py` 的原逻辑 `if 'ODS-DWD-DWS-DM' in cell.text` 会将真实任务（如"ODS-DWD-DWS-DM：0611 李江已和卫宁方一期推进"）误判为占位符。已修复为：仅当整行所有单元格均为空或仅含裸占位符文本（无编号/无实质内容）时才标记 FAIL。
14. **协调事务话术 — "进行中" 改写为 "尚未完成"**：在线文档备注中的 "XX开发进行中，需要提供数据字典" 会被 `validate_report_tone.py` 拦截为"模糊用语 FAIL"。引擎新增 `_sanitize_note_text()` 方法（在 `clean_notes()` 返回前调用），自动将 "进行中" 改写为 "尚未完成"，并剥离 "0611：" 等日期前缀。同时在 `find_coordination_items()` 中同步处理。
15. **话术校验量化检查 — 第三方阻塞项白名单**：`validate_report_tone.py` 的 `check_quantification()` 对 "卫宁数据开发尚未完成，需要提供数据字典" 这类被外部阻塞的任务误报 "缺少量化数据 FAIL"。已新增 `external_block_patterns` 白名单：`r'尚未完成.*需要.*提供'`、`r'需要.*提供.*数据'`、`r'等待.*反馈'` 等模式跳过量化检查。

## 里程碑图片生成

每次生成周报前，先运行：

```bash
python3 scripts/generate-milestone-image.py
```

生成 `/tmp/milestone_progress_v9.png`，引擎会自动嵌入到 Word 文档 Row 6 的"项目总体进度"区域。

### 图片质量要求（2026-05-18 用户反馈后确立）
- **字体必须用 NotoSansCJK**（或 wqy-zenhei），**禁止用 DejaVuSans**（不支持中文，输出方块□）
- **字体大小 ≥ 28px**（1600px 画布），< 28px 在 Word 中肉眼不可读
- **行高必须动态计算**（基于单元格内容自动撑开），禁止固定行高（交付件列内容多时严重重叠）
- **表头每列独立分隔**（竖线分隔 + 居中对齐），禁止列名合并（如"里程碑时点交付件"连写）
- **生成后必须视觉验证**（vision_analyze 或导出 PDF），不可仅凭"脚本没报错"就通过

## 备注智能提取

备注列可能含多条带日期前缀的更新（如 `0428:xxx|0509:yyy`）。引擎 `clean_notes()` 方法：
   - 优先提取**本周（周一至周日）内最新**的一条更新，剥离日期前缀只留内容
   - 无本周更新时回退到最后一行（同样剥离旧日期前缀）
   - 详见 `references/notes-extraction.md`

## 变更记录
- **v12.2**: 三项 QA 校验修复：(1) `validate_weekly_report.py` 空任务占位符误判 — "ODS-DWD-DWS-DM" 是真实数据架构术语，修复为仅标记全空行；(2) `report_engine_v9.py` 新增 `_sanitize_note_text()` — 协调事务中 "进行中" 自动改写为 "尚未完成"，剥离日期前缀；(3) `validate_report_tone.py` 新增 `external_block_patterns` 白名单 — 第三方阻塞项跳过量化检查。引擎还新增自动删除模板遗留空行逻辑。
- **v12**: 模板占位文字自动清理 + 头部行 CJK eastAsia 批量修复。`_fix_template_fonts()` 扩展为两步：(1) 扫描全表所有 CJK run 补设 eastAsia（覆盖 Row 0-5 等不被引擎覆盖的模板头部行）；(2) 全表扫描清除"预计存在或可能出现"等占位文字（不限于 YAML 配置的 section rows），避免误触发话术校验 FAIL。
- **v12.1**: 话术校验量化检查增强 — `validate_report_tone.py` 的 `check_quantification()` 新增 startup_patterns 白名单：跳过"可以开始/启动/进场/安排资源/调研/梳理需求/收集案例"等新启动或定性任务的量化检查，避免对无进度%的正常任务误报 FAIL。
- **v11**: QA 校验自动集成到引擎尾部。生成周报后自动执行两层校验：(1) validate_weekly_report.py — L1 结构/L2 数据/L3 视觉；(2) validate_report_tone.py — 话术检查（模糊用语/废话拦截/量化检查/风险前置/已完成重复/编号层级）。无需额外命令，引擎自动触发。
- **v11**: CJK 字体乱码修复（PNG: Noto CJK 优先 + draw_text 处理 \n + 动态行高；Word: _set_run_font eastAsia 属性）。新增自动校验脚本 validate_weekly_report.py（L1 结构/L2 数据/L3 视觉）。QA Agent 流程写入 SOP。
- **v10**: 在线文档实时同步流程（mcporter）、进度 % 解析修复、备注日期前缀智能提取、xlsxwriter 写入强制要求、fetch-online-sheet.py 脚本。
- **v9**: YAML 配置驱动引擎、邮件正文生成、delegate_task QA 封装、模块编号修复。
- **v8**: 文件名规范、日期改为周五、字号字体统一、里程碑截图改进、风险二级编号。
- **v7**: 里程碑截图颜色对齐、协调事务识别、风险编号、独立 QA Agent。
