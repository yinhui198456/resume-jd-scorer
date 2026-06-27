# CJK 字体乱码修复记录

## 根因

周报中的中文字符显示为方块（tofu），出现在两个环节：

### 1. 里程碑进度图（PNG，Pillow）

`generate-milestone-image.py` 的 `get_font()` 原优先使用 `DejaVuSans.ttf`（纯英文字体），中文字符无法渲染。

**修复**：
- 字体 fallback 顺序：`NotoSansCJK-Regular.ttc` → `NotoSerifCJK-Regular.ttc` → `wqy-zenhei.ttc` → `DejaVuSans.ttf`
- `draw_text()` 必须按 `\n` 分段（`text.split('\n')`），每段独立 wrap，否则交付件等多行文本会重叠
- 行高必须动态计算（`calc_row_height()`），根据每列字符数 × 字体高度 × 行间距自动调整

### 2. Word 文档表格（python-docx）

`run.font.name = "微软雅黑"` 只对拉丁字体有效，CJK 字符需额外设置 `eastAsia` 属性。

**修复**：
```python
def _set_run_font(self, run, size=None, bold=None):
    run.font.name = self.font_name
    rpr = run._element.get_or_add_rPr()
    rFonts = rpr.find(qn('w:rFonts'))
    if rFonts is None:
        from lxml import etree
        rFonts = etree.SubElement(rpr, qn('w:rFonts'))
    rFonts.set(qn('w:eastAsia'), self.font_name)
    if size: run.font.size = size
    if bold: run.font.bold = bold
```
所有 `run.font.name/size/bold` 三行赋值替换为 `self._set_run_font(run, size=X, bold=Y)`。

### 3. 模板头部行 CJK 字体（2026-05-17 新增）

引擎只覆盖 Row 6/8/10/12 等数据行，但模板的 Row 0-5（项目名称、项目总监等）包含中文 run 且未设置 eastAsia。`validate_weekly_report.py` 的 L3 校验会检测全表所有行，导致 FAIL。

**修复**：引擎在 `Document(template_path)` 后立即调用 `_fix_template_fonts(doc)`，遍历全表所有 run，对含 CJK 字符的 run 补设 eastAsia。

### 4. 模板占位文字触发言术校验（2026-05-17 新增）

模板 Row 11（"风险"章节标题行）包含占位文字"预计存在或可能出现的风险及解决方案"，被 `validate_report_tone.py` 的"不确定语气"规则拦截为 FAIL。

**修复**：`_fix_template_fonts()` 遍历全表所有段落，清除包含占位关键词（"预计存在""可能出现""请在此处填写""示例：""风险描述""解决方案""协调事项"）的段落内容。

## 校验

`validate_weekly_report.py` 的 L3 视觉层自动检测：
- CJK run 是否设置 `eastAsia`（检查全表所有行）
- 方块字符计数（\uFFFD + \u25A1）
- 里程碑图片嵌入数量

`validate_report_tone.py` 的话术层自动检测：
- 模糊用语（"进行中""推进中"等）
- 不确定语气（"预计存在""可能出现""可能""也许"等）
- 废话拦截（"大家好""希望大家继续努力"等）
- 量化检查、风险前置、编号层级
