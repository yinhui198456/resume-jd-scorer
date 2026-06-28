#!/usr/bin/env python3
"""生成里程碑进度图 (供 report_engine_v9.py 嵌入 Word)。v3

输出: /tmp/milestone_progress_v9.png (硬编码路径，引擎中引用)
用法: python3 generate-milestone-image.py

依赖: Pillow (PIL), NotoSansCJK 字体

v3 修复 (2026-05-18):
- 字体: NotoSansCJK-Regular (DejaVuSans 不支持中文→方块□)
- 行高: 动态计算 (wrap_text + calc_required_height)，不再固定 260px
- 表头: 每列独立分隔线 + 居中对齐，不再列名合并
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import yaml

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")
OUTPUT_PATH = "/tmp/milestone_progress_v9.png"

# 默认配置；若存在 config.yaml，则优先从 config.yaml 读取
DEFAULT_CONFIG = {
    "width": 1600,
    "header_height": 50,
    "font_size": 28,
    "font_size_bold": 32,
    "cell_padding_x": 12,
    "cell_padding_y": 10,
    "line_spacing": 1.5,
    "colors": {
        "header_bg": "#5DC5F9",
        "header_border": "#00A3F5",
        "row_completed": "#EAFAF1",
        "row_active": "#FFF9E3",
        "row_future": "#F2F2F2",
        "text": "#333333",
        "border": "#B0B0B0",
    },
    "columns": [
        {"name": "编号", "width": 65},
        {"name": "里程碑", "width": 170},
        {"name": "里程碑标志", "width": 290},
        {"name": "里程碑时点", "width": 155},
        {"name": "交付件", "width": 550},
        {"name": "状态", "width": 120},
        {"name": "付款比例", "width": 150},
    ],
    "display_map": {
        "编号": "编号",
        "里程碑": "里程碑名称",
        "里程碑标志": "里程碑标志",
        "里程碑时点": "里程碑时点",
        "交付件": "交付件",
        "状态": "状态",
        "付款比例": "付款比例",
    }
}


def load_config():
    """Load milestone image config from config.yaml if present."""
    cfg = DEFAULT_CONFIG.copy()
    if not os.path.exists(CONFIG_PATH):
        return cfg

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            doc = yaml.safe_load(f)
    except Exception as e:
        print(f"  ⚠️ 读取 config.yaml 失败，使用默认配置: {e}")
        return cfg

    source = doc.get('source', {}) if doc else {}
    mi = doc.get('milestone_image', {}) if doc else {}

    # XLSX path
    xlsx = source.get('xlsx_path')
    if xlsx:
        if not os.path.isabs(xlsx):
            xlsx = os.path.normpath(os.path.join(PROJECT_DIR, xlsx))
        cfg['xlsx_path'] = xlsx

    # Display map
    dmap = source.get('milestone_display_map')
    if dmap:
        cfg['display_map'] = dmap

    # Image dimensions and style
    for key in ('width', 'header_height', 'font_size', 'font_size_bold'):
        if key in mi:
            cfg[key] = mi[key]

    # Padding / spacing defaults if not in config
    cfg['cell_padding_x'] = mi.get('cell_padding_x', cfg['cell_padding_x'])
    cfg['cell_padding_y'] = mi.get('cell_padding_y', cfg['cell_padding_y'])
    cfg['line_spacing'] = mi.get('line_spacing', cfg['line_spacing'])

    # Colors
    colors = mi.get('colors')
    if colors:
        cfg['colors'].update(colors)

    # Columns
    columns = mi.get('columns')
    if columns:
        cfg['columns'] = columns

    return cfg

def parse_excel(filepath):
    """Parse sheet 2 (02-项目里程碑) from xlsx via XML."""
    if not os.path.exists(filepath):
        return []
    zf = zipfile.ZipFile(filepath)
    ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    try:
        ss_root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    ss = []
    for si in ss_root:
        txt = ''.join([t.text or '' for t in si.findall('.//ss:t', ns) + si.findall('.//t') if t.text])
        ss.append(txt)
    sheet_path = 'xl/worksheets/sheet2.xml'
    if sheet_path not in zf.namelist():
        return []
    try:
        root = ET.fromstring(zf.read(sheet_path))
    except Exception:
        return []
    header_map = {}
    rows = []
    for row in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        cells = {}
        for c in row.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            ref = c.get('r', '')
            col = ''.join(filter(str.isalpha, ref))
            v_node = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            if c.get('t') == 's' and v_node is not None:
                val = ss[int(v_node.text)] if v_node.text else ''
            elif v_node is not None:
                val = v_node.text
            else:
                val = ''
            cells[col] = val
        vals = list(cells.values())
        if '里程碑名称' in vals or '里程碑标志' in vals:
            header_map = cells
        elif header_map and any(cells.values()):
            row_dict = {header_map.get(k): v for k, v in cells.items()}
            if any(v.strip() if isinstance(v, str) else str(v).strip() for v in row_dict.values()):
                rows.append(row_dict)
    return rows

_FONT_CACHE = {}

def _load_font(ttc_path, size):
    key = (ttc_path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(ttc_path, size, index=0)
    return _FONT_CACHE[key]

def get_font(size):
    for path in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]:
        if os.path.exists(path):
            try:
                return _load_font(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def get_bold_font(size):
    for path in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]:
        if os.path.exists(path):
            try:
                return _load_font(path, size)
            except Exception:
                pass
    return get_font(size)

def wrap_text(text, font, max_width):
    """Wrap text into lines that fit within max_width (CJK char-by-char)."""
    if not text:
        return ['']
    text = str(text)
    lines = []
    current_line = ''
    current_width = 0
    for ch in text:
        if ch == '\n':
            lines.append(current_line)
            current_line = ''
            current_width = 0
            continue
        ch_width = font.getlength(ch)
        if current_line and current_width + ch_width > max_width:
            lines.append(current_line)
            current_line = ch
            current_width = ch_width
        else:
            current_line += ch
            current_width += ch_width
    if current_line:
        lines.append(current_line)
    return lines if lines else ['']

def calc_line_height(font, line_spacing=1.5):
    return int(font.getbbox("Hg国")[3] * line_spacing)

def calc_required_height(text, font, max_width, line_spacing):
    lines = wrap_text(text, font, max_width)
    line_h = calc_line_height(font, line_spacing)
    return line_h * len(lines)

def main():
    print("📊 生成里程碑进度图 v3...")
    cfg = load_config()
    xlsx_path = cfg.get('xlsx_path', os.path.join(PROJECT_DIR, "data", "金坛二期项目跟进表.xlsx"))
    rows = parse_excel(xlsx_path)
    if not rows:
        print("  ⚠️ 未找到里程碑数据"); return

    colors = cfg["colors"]
    cols = cfg["columns"]
    dmap = cfg["display_map"]

    mapped_rows = []
    for r in rows:
        m = {}
        for dn, dn_data in dmap.items():
            val = r.get(dn_data, '').strip() if r.get(dn_data) else ''
            m[dn] = val
        if m.get('编号') or m.get('里程碑'):
            mapped_rows.append(m)
    if not mapped_rows:
        print("  ⚠️ 无有效数据"); return

    font = get_font(cfg["font_size"])
    font_bold = get_bold_font(cfg["font_size_bold"])
    line_h = calc_line_height(font, cfg["line_spacing"])
    pad_x = cfg["cell_padding_x"]
    pad_y = cfg["cell_padding_y"]

    # Dynamic row heights
    row_heights = []
    for row in mapped_rows:
        max_h = line_h
        for col in cols:
            val = row.get(col["name"], '')
            avail_w = col["width"] - pad_x * 2
            needed = calc_required_height(val, font, avail_w, cfg["line_spacing"])
            if needed + pad_y * 2 > max_h:
                max_h = needed + pad_y * 2
        row_heights.append(max_h)

    total_w = cfg["width"]
    header_h = cfg["header_height"]
    total_h = header_h + sum(row_heights)

    img = Image.new('RGB', (total_w, total_h), 'white')
    draw = ImageDraw.Draw(img)

    # Header with separators
    draw.rectangle([0, 0, total_w, header_h], fill=colors["header_bg"])
    draw.line([(0, header_h), (total_w, header_h)], fill=colors["header_border"], width=3)

    x = 0
    for col in cols:
        draw.line([(x, 0), (x, header_h)], fill=colors["header_border"], width=2)
        text_w = font_bold.getlength(col["name"])
        text_h = font_bold.getbbox(col["name"])[3]
        tx = x + int((col["width"] - text_w) / 2)
        ty = int((header_h - text_h) / 2)
        draw.text((tx, ty), col["name"], fill=colors["text"], font=font_bold)
        x += col["width"]
    draw.line([(total_w, 0), (total_w, header_h)], fill=colors["header_border"], width=2)

    # Data rows
    y = header_h
    for i, row in enumerate(mapped_rows):
        y1 = y
        y2 = y + row_heights[i]

        status = row.get('状态', '').strip()
        if status == '已完成': bg = colors["row_completed"]
        elif status == '进行中': bg = colors["row_active"]
        else: bg = colors["row_future"]

        draw.rectangle([0, y1, total_w, y2], fill=bg)

        x = 0
        for col in cols:
            val = row.get(col["name"], '')
            avail_w = col["width"] - pad_x * 2
            lines = wrap_text(val, font, avail_w)
            ty = y1 + pad_y
            for line in lines:
                draw.text((x + pad_x, ty), line, fill=colors["text"], font=font)
                ty += line_h
            draw.line([(x + col["width"], y1), (x + col["width"], y2)], fill=colors["border"], width=1)
            x += col["width"]

        draw.line([(0, y2), (total_w, y2)], fill=colors["border"], width=1)
        y = y2

    img.save(OUTPUT_PATH, quality=95)
    print(f"  ✅ {OUTPUT_PATH} ({total_w}x{total_h}px, {len(mapped_rows)}行)")

if __name__ == "__main__":
    main()
