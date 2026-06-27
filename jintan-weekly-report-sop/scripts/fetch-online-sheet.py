#!/usr/bin/env python3
"""从腾讯文档在线表格拉取最新数据，写入本地 xlsx。

用法: python3 fetch-online-sheet.py <file_id>

依赖: mcporter (已配置 tencent-sheetengine MCP server)
"""

import sys
import os
import subprocess
import json
import csv
import xlsxwriter
from io import StringIO

SHEETS = {
    "01-项目计划": {"id": None, "cols": 20},      # sheet_id 从 get_sheet_info 获取
    "02-项目里程碑": {"id": None, "cols": 27},
    "04-应用问题跟踪表": {"id": None, "cols": 30},
}

def get_sheet_info(file_id):
    """获取所有 sheet 的 id 和名称映射。"""
    cmd = ["mcporter", "call", "tencent-sheetengine.get_sheet_info", f"file_id={file_id}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(res.stdout)
    mapping = {}
    for s in data.get("sheets", []):
        mapping[s["sheet_name"]] = s["sheet_id"]
    return mapping

def get_cell_data(file_id, sheet_id, end_col=26):
    """拉取指定 sheet 的 CSV 数据。"""
    cmd = [
        "mcporter", "call", "tencent-sheetengine.get_cell_data",
        f"file_id={file_id}", f"sheet_id={sheet_id}",
        "start_row=0", "start_col=0", f"end_row=200", f"end_col={end_col}",
        "return_csv=true"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: {res.stderr}", file=sys.stderr)
        return None
    data = json.loads(res.stdout)
    csv_content = data.get("csv_data", "")
    if not csv_content:
        return []
    reader = csv.reader(StringIO(csv_content))
    return [r for r in reader]

def main():
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) < 2:
        print("Usage: python3 fetch-online-sheet.py <file_id>")
        sys.exit(1)

    file_id = sys.argv[1]
    output_path = os.path.join(PROJECT_DIR, "data", "金坛二期项目跟进表.xlsx")

    print(f"📡 正在获取 sheet_id 映射...")
    name_to_id = get_sheet_info(file_id)
    print(f"   找到 {len(name_to_id)} 个 sheet: {list(name_to_id.keys())}")

    wb = xlsxwriter.Workbook(output_path)

    for name, conf in SHEETS.items():
        sheet_id = name_to_id.get(name)
        if not sheet_id:
            print(f"   ⚠️  跳过 {name}: 在线文档中不存在")
            continue

        print(f"   📥 拉取 {name}...")
        data = get_cell_data(file_id, sheet_id, end_col=conf["cols"])
        if not data:
            print(f"   ⚠️  {name}: 数据为空")
            continue

        # 跳过标题行（首行不含"序号"/"编号"）
        first_row_vals = [str(v).strip() for v in data[0] if v]
        if "序号" not in first_row_vals and "编号" not in first_row_vals:
            print(f"   ⏭️  跳过标题行: {data[0][0]}")
            data = data[1:]

        ws = wb.add_worksheet(name)
        for r_idx, row in enumerate(data):
            for c_idx, val in enumerate(row):
                if val:
                    try:
                        val = float(val) if "." in val else int(val)
                    except (ValueError, TypeError):
                        pass
                    ws.write(r_idx, c_idx, val)
        print(f"   ✅ 写入 {len(data)} 行")

    wb.close()
    print(f"\n💾 已保存: {output_path}")

if __name__ == "__main__":
    main()
