# 金坛二期周报 — 手动生成方案

当 `report_engine_v9.py` 不存在时的备选流程。

## 1. 读取 xlsx 数据源

```python
from python_calamine import CalamineWorkbook
wb = CalamineWorkbook.from_path('./data/金坛二期项目跟进表.xlsx')

# 01-项目计划：第1行是合并标题，第2行才是列头
sheet = wb.get_sheet_by_name('01-项目计划')
data = sheet.to_python()
headers = data[1]  # 实际列头
plan_rows = []
for row in data[2:]:
    if any(v is not None for v in row):
        obj = {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
        plan_rows.append(obj)
```

## 2. 复制并修改 docx 模板

```python
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
import shutil

src = './templates/常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260420-0424.docx'
dst = './output/常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260427-0430.docx'
shutil.copy(src, dst)

doc = Document(dst)
# 更新标题/日期，替换 table rows[6,8,10,12]
# 统一字体为微软雅黑 10.5pt
```

## 3. 里程碑截图生成

用 Pillow 绘制 PNG 表格图（2x 抗锯齿），用 NotoSansCJK 字体，颜色对应 Excel 原始 Sheet：
- 已完成=#EAFAF1(绿底)+状态文字#548235
- 进行中=#FFF9E3(黄底)+状态文字#BF8F00
- 未开始=#F2F2F2(灰底)+状态文字#999999

插入 docx: `run.add_picture(img_path, width=Inches(6.5))`

## 4. 过滤规则

- 本周计划：排除"项目管理"；排除历史已完成（状态=完成 AND 实际完成<本周周一）
- 下周计划：计划开始在本周后~下周五，且未开始/进行中
- 需协调：计划完成<今天 且 进度<100%，或含外部关键词
- 遗留问题：04-应用问题跟踪表 中状态≠"已修复"的项
