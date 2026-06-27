# 金坛二期周报 SOP — Claude Code 迁移部署手册

> 从 Hermes Agent project profile 迁移至 Claude Code 环境。
> 打包时间: 2026-06-21 | SOP 版本: v12.2

---

## 1. 文件清单

```
jintan-weekly-report-sop/
├── SKILL.md                          # 主 SOP 文档（完整工作流 + Pitfalls）
├── config.yaml                       # 周报 YAML 配置（列名/格式/过滤/章节）
├── DEPLOYMENT.md                     # 本部署手册
├── scripts/
│   ├── fetch-online-sheet.py         # 从腾讯文档拉取最新数据（mcporter）
│   ├── fetch-jintan-data.py          # 金坛专用数据拉取（硬编码 sheet_id）
│   ├── generate-milestone-image.py   # 里程碑进度 PNG 图（Pillow + NotoSansCJK）
│   ├── validate_report_tone.py       # 话术校验（模糊用语/量化/风险/编号）
│   ├── project_report.py             # 旧版引擎 v5（XML 解析，硬编码）
│   └── jintan_report.py              # 旧版引擎 v3（XML 解析，硬编码）
└── references/
    ├── cjk-font-fix.md               # CJK 字体乱码修复记录
    ├── manual-report-generation.md   # 手动生成方案（引擎缺失时的备选）
    ├── notes-extraction.md           # 备注列日期前缀提取逻辑
    └── progress-parsing-fix.md       # 进度 % 解析补丁
```

**⚠️ 关键缺失文件（SOP 中引用但不存在）：**

| 文件 | SOP 中的角色 | 状态 |
|------|-------------|------|
| `scripts/report_engine_v9.py` | YAML 配置驱动的通用生成引擎（v9+） | ❌ 不存在，仅有 v3/v5 旧版 |
| `scripts/validate_weekly_report.py` | L1 结构 / L2 数据 / L3 视觉 QA 校验 | ❌ 不存在 |

这意味着 SOP 描述的核心引擎尚未实现。当前可用的脚本是早期迭代版本（v3/v5），不具备 YAML 配置驱动能力。

---

## 2. 依赖清单

### Python 包
```
python-docx          # Word 文档读写
xlsxwriter           # 写入 xlsx（必须，openpyxl 不生成 sharedStrings.xml）
python-calamine      # 读取 xlsx（Python 3.12 下 openpyxl 有 bug）
Pillow               # 里程碑 PNG 图生成
lxml                 # XML 操作（python-docx 依赖）
pyyaml               # YAML 配置解析（v9 引擎需要）
```

### 系统依赖
```
NotoSansCJK-Regular.ttc    # CJK 字体（PNG 图 + Word 文档）
  路径: /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
  备选: wqy-zenhei.ttc

mcporter CLI               # 腾讯文档 MCP 调用（fetch-online-sheet.py 需要）
  已配置: tencent-sheetengine server
```

### 安装命令
```bash
pip install python-docx xlsxwriter python-calamine Pillow lxml pyyaml
apt-get install fonts-noto-cjk  # 或手动下载 NotoSansCJK
```

---

## 3. 外部依赖

### 3.1 腾讯文档
- **在线文档 ID**: `DYm9pRHBFa0NMRmta`
- **Sheet 映射**:
  - `01-项目计划` → sheet_id: `uj7enc`（第 1 行为合并标题，第 2 行为实际列头）
  - `02-项目里程碑` → sheet_id: `hxxrnm`
  - `04-应用问题跟踪表` → sheet_id: `BB08J2`

### 3.2 Word 模板
- **模板路径**: `docs/常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260420-0424.docx`
- 模板包含预定义的表格结构，引擎填充 Row 6/8/10/12

### 3.3 本地数据文件
- **xlsx 路径**: `docs/金坛二期项目跟进表.xlsx`
- 由 `fetch-online-sheet.py` 或 `fetch-jintan-data.py` 从在线文档拉取

---

## 4. 执行流程

### 4.1 完整流程（推荐）
```bash
# Step 0: 从在线文档拉取最新数据
python3 scripts/fetch-online-sheet.py DYm9pRHBFa0NMRmta

# Step 0b: 生成里程碑进度图（必须在引擎前运行）
python3 scripts/generate-milestone-image.py

# Step 1: 生成周报（使用现有可用引擎）
python3 scripts/jintan_report.py       # v3 引擎
# 或
python3 scripts/project_report.py      # v5 引擎（含 SOW 上下文语义重写）

# Step 2: 话术校验
python3 scripts/validate_report_tone.py <生成的docx路径>

# Step 3: 发送到飞书群
cd docs && lark-cli im +messages-send \
  --chat-id "oc_63e348c1b3c23f50ad587113be8bfa4a" \
  --file "常州市金坛第一人民医院数据指挥中心二期项目-工作周报-YYYYMMDD-MMDD.docx"
```

### 4.2 v9 YAML 引擎（需自行实现）
SOP 中描述的 `report_engine_v9.py` 核心能力：
- 读取 `config.yaml` 配置，不绑定特定项目
- 自动触发 `validate_weekly_report.py`（L1/L2/L3）和 `validate_report_tone.py`（话术）
- `_set_run_font()` 统一设置 CJK eastAsia 字体
- `_fix_template_fonts()` 清理模板占位文字 + 补设头部行字体
- `_sanitize_note_text()` 将"进行中"改写为"尚未完成"
- `clean_notes()` 智能提取本周最新备注
- 自动删除模板遗留空行

这些能力目前分散在 v3/v5 脚本中，需要通过 Claude Code 实现统一的 v9 引擎。

---

## 5. Claude Code 迁移步骤

### 5.1 环境准备
```bash
# 1. 创建项目目录
mkdir -p ~/jintan-report/{scripts,docs,config,refs}

# 2. 安装 Python 依赖
pip install python-docx xlsxwriter python-calamine Pillow lxml pyyaml

# 3. 安装 CJK 字体
apt-get install -y fonts-noto-cjk

# 4. 验证字体
fc-list | grep -i "noto sans cjk"
```

### 5.2 文件迁移
将打包的文件复制到新环境：
- `SKILL.md` → 项目根目录（作为完整参考文档）
- `config.yaml` → `config/jintan_report.yaml`
- `scripts/*.py` → `scripts/`
- `references/*.md` → `refs/`

**需要额外准备的文件（不在打包中）：**
- Word 模板 `.docx` 文件（从原环境 `docs/` 目录复制）
- 已存在的 `金坛二期项目跟进表.xlsx`（或运行 fetch 脚本重新拉取）

### 5.3 mcporter 替代方案
Claude Code 环境中可能没有 `mcporter` CLI。替代方案：

**方案 A**: 保留 mcporter（如果可安装）
```bash
# 检查是否可用
mcporter list
```

**方案 B**: 使用腾讯文档 API 直接调用
需要配置腾讯文档开发者应用的 AppID/AppSecret，通过 HTTP API 获取数据。

**方案 C**: 手动上传 xlsx
定期手动下载在线文档为 xlsx，放到 `docs/` 目录。

### 5.4 实现 v9 引擎（Claude Code 任务）
建议用 Claude Code 实现以下任务：

```
Task: 实现 report_engine_v9.py
Input: config/jintan_report.yaml + docs/*.xlsx
Output: 格式正确的 .docx 周报

要求:
1. 读取 YAML 配置，动态解析 sheet/列名/过滤规则
2. 使用 python-calamine 读取 xlsx（不用 openpyxl）
3. 使用 xlsxwriter 写入 xlsx（fetch 脚本中）
4. _set_run_font() 设置 CJK eastAsia
5. _fix_template_fonts() 清理模板
6. _sanitize_note_text() 处理"进行中"
7. clean_notes() 智能提取备注
8. 自动触发 validate_report_tone.py
9. 生成里程碑图并嵌入 Word
```

---

## 6. 已知 Pitfalls（必须遵守）

1. **读 xlsx 用 calamine，写 xlsx 用 xlsxwriter** — openpyxl 写入不生成 sharedStrings.xml，引擎 XML 解析器会读出行数为 0
2. **CJK 字体必须用 NotoSansCJK** — DejaVuSans 不支持中文，输出方块 □
3. **Sheet ID 是文件内物理序号** — sheet1.xml → "1"，不是在线文档的 sheet_id（如 uj7enc）
4. **01-项目计划第 1 行是合并标题** — 第 2 行才是实际列头，需要跳过
5. **进度列含 % 符号** — 需要剥离 `%` 后再 float 转换
6. **"ODS-DWD-DWS-DM" 是真实术语** — 不要当占位符过滤掉
7. **"进行中" 必须改写为 "尚未完成"** — 否则触发话术校验 FAIL
8. **Word 模板中的占位文字必须清除** — "预计存在或可能出现"等会触发话术 FAIL
9. **模板头部行（Row 0-5）需要补设 eastAsia** — 不被引擎覆盖但 QA 会检查
10. **飞书发送 Word 附件不能用 MEDIA: 标签** — 必须用 lark-cli --file

---

## 7. QA 校验矩阵

| 层级 | 脚本 | 检查项 | 阻塞等级 |
|------|------|--------|---------|
| L1 结构 | validate_weekly_report.py（需实现） | Markdown/编号/空任务 | FAIL |
| L2 数据对照 | validate_weekly_report.py（需实现） | 日期/文件名/条目数 | FAIL |
| L3 视觉 | validate_weekly_report.py（需实现） | 字体/CJK/图片 | FAIL |
| L4 话术 | validate_report_tone.py（已有） | 模糊用语/量化/风险 | FAIL |

---

## 8. 配置文件速查

| 配置段 | 用途 | 关键值 |
|--------|------|--------|
| `project` | 项目信息 | name, short_name |
| `source.sheets` | Sheet 物理序号 | plan:"1", milestone:"2", issues:"3" |
| `source.columns` | 列名映射 | 工作单元/任务阶段/任务/备注/进度/状态 |
| `date.report_date` | 报告日期 | friday（周五） |
| `format.font` | 字体 | 微软雅黑 |
| `filter.this_week` | 本周过滤 | 排除已完成/项目管理/历史已完成 |
| `coordination.external_keywords` | 外部阻塞词 | 调研/确认/反馈/待定/业务方等 |
| `milestone_image` | 里程碑图配置 | 颜色/列宽/字体 |

---

## 9. 文件输出路径约定

```
docs/
├── 金坛二期项目跟进表.xlsx                    # 数据源（从在线文档拉取）
├── 常州市金坛第一人民医院...工作周报-模板.docx  # Word 模板
└── 常州市金坛第一人民医院...工作周报-YYYYMMDD-MMDD.docx  # 生成结果

/tmp/
└── milestone_progress_v9.png                  # 里程碑进度图（临时）
```
