#!/usr/bin/env python3
"""从腾讯文档在线表格拉取金坛二期最新数据，写入本地 xlsx。

用法: python3 fetch-jintan-data.py

依赖: mcporter (已配置 tencent-sheetengine MCP server)
      xlsxwriter (写入 xlsx，不可用 openpyxl)

Pitfalls:
- 必须用 xlsxwriter 写入，openpyxl 不生成 sharedStrings.xml 导致引擎 XML 解析器读出行数为 0
- 每次 mcporter 调用后 sleep 3s 避免触发腾讯文档限流 (400007)
"""

import subprocess
import json
import csv
import xlsxwriter
from io import StringIO
import sys
import time
import os

FILE_ID = "DYm9pRHBFa0NMRmta"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(PROJECT_DIR, "data", "金坛二期项目跟进表.xlsx")

SHEETS = [
    {"name": "01-项目计划", "sheet_id": "uj7enc", "cols": 20},
    {"name": "02-项目里程碑", "sheet_id": "hxxrnm", "cols": 27},
    {"name": "04-应用问题跟踪表", "sheet_id": "BB08J2", "cols": 30},
]

def get_cell_data(sheet_id, end_col=26):
    cmd = [
        "mcporter", "call", "tencent-sheetengine.get_cell_data",
        f"file_id={FILE_ID}", f"sheet_id={sheet_id}",
        "start_row=0", "start_col=0", "end_row=200", f"end_col={end_col}",
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
    print(f"📡 正在从腾讯文档拉取金坛二期最新数据 (file_id={FILE_ID})...")
    
    wb = xlsxwriter.Workbook(OUTPUT_PATH)
    
    for sheet_conf in SHEETS:
        name = sheet_conf["name"]
        sheet_id = sheet_conf["sheet_id"]
        cols = sheet_conf["cols"]
        
        print(f"   📥 拉取 {name}...")
        data = get_cell_data(sheet_id, end_col=cols)
        time.sleep(3)  # rate limit delay
        
        if not data:
            print(f"   ⚠️  {name}: 数据为空")
            continue
        
        # 跳过标题行（首行不含"序号"/"编号"/"工作单元"）
        first_row_vals = [str(v).strip() for v in data[0] if v]
        has_header = any(kw in first_row_vals for kw in ["序号", "编号", "工作单元"])
        if not has_header:
            print(f"   ⏭️  跳过标题行: {data[0][0] if data[0] else '?'}")
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
    print(f"\n💾 已保存: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
