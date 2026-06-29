#!/usr/bin/env python3
"""搜索最近上传的文件，供 resume-jd-scorer skill 使用。

搜索路径：.codepilot-uploads/ 和 /tmp/（限定前缀）
按修改时间排序，列出最近 N 个候选文件。

用法：
    python3 find_uploads.py [--limit 5] [--type resume|jd|all] [--with-name]

输出：文件路径列表（stdout，每行一个）
"""

import datetime
import os
import sys
import time

import magic

# 导入姓名提取函数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from parse_file import extract_candidate_name, parse_pdf, parse_docx, parse_txt, parse_image, detect_mime_type, MIME_TO_FORMAT

UPLOAD_DIRS = [
    "/opt/personal-agent-workspace/.codepilot-uploads",
    "/tmp",
]

# /tmp/ 下只搜索这些前缀，避免扫描全系统文件
TMP_FILE_PREFIXES = ("resume", "file_v3", "test_resume")

# 简历文件大小上限（10MB），排除大型 ZIP 等误匹配
MAX_RESUME_SIZE = 10 * 1024 * 1024

# 文件保留时间（7 天）
MAX_AGE_SECONDS = 7 * 86400

# 简历/文档 MIME types
RESUME_MIME_TYPES = frozenset([
    "application/pdf",
    "application/zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/webp",
])

JD_MIME_TYPES = frozenset([
    "application/pdf",
    "text/plain",
])


def find_recent_files(limit: int = 10, file_type: str = "all") -> list[tuple[str, str, float]]:
    """返回 [(path, mime_type, mtime), ...]，按 mtime 降序排列。"""
    candidates = []
    now = time.time()

    for upload_dir in UPLOAD_DIRS:
        if not os.path.isdir(upload_dir):
            continue
        for fname in os.listdir(upload_dir):
            # /tmp/ 限定前缀，避免扫描无关文件
            if upload_dir == "/tmp":
                if not any(fname.startswith(prefix) for prefix in TMP_FILE_PREFIXES):
                    continue

            fpath = os.path.join(upload_dir, fname)
            if not os.path.isfile(fpath):
                continue

            # 跳过太旧的文件
            mtime = os.path.getmtime(fpath)
            if now - mtime > MAX_AGE_SECONDS:
                continue

            try:
                mime = magic.from_file(fpath, mime=True)
            except Exception:
                continue

            # 排除 inode 等非常规文件
            if mime.startswith("inode/") or mime.startswith("application/x-"):
                continue

            # 简历文件大小过滤
            if file_type == "resume" and mime in ("application/zip",):
                if os.path.getsize(fpath) > MAX_RESUME_SIZE:
                    continue

            # 类型过滤
            allowed = RESUME_MIME_TYPES if file_type == "resume" else \
                      JD_MIME_TYPES if file_type == "jd" else None
            if allowed is not None and mime not in allowed:
                continue

            candidates.append((fpath, mime, mtime))

    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:limit]


def _parse_resume_text(fpath: str, mime: str) -> str:
    """根据 MIME type 解析简历文件为文本。"""
    fmt = MIME_TO_FORMAT.get(mime)
    if fmt is None:
        return ""
    parsers = {
        "txt": parse_txt,
        "docx": parse_docx,
        "pdf": parse_pdf,
        "image": parse_image,
    }
    try:
        return parsers[fmt](fpath)
    except Exception:
        return ""


def main():
    limit = 5
    file_type = "all"
    with_name = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            file_type = args[i + 1]
            i += 2
        elif args[i] == "--with-name":
            with_name = True
            i += 1
        else:
            i += 1

    files = find_recent_files(limit=limit, file_type=file_type)

    if not files:
        print("未找到最近上传的文件", file=sys.stderr)
        sys.exit(1)

    for fpath, mime, mtime in files:
        ts = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        size_kb = os.path.getsize(fpath) // 1024

        # 提取候选人姓名（仅对简历类型，或显式 --with-name）
        name = ""
        if with_name or file_type == "resume":
            if mime in ("application/pdf", "image/png", "image/jpeg", "image/webp",
                        "application/zip",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
                text = _parse_resume_text(fpath, mime)
                name = extract_candidate_name(text) or ""

        name_col = f"  {name}" if name else ""
        print(f"{ts}  {size_kb:>5}KB  {mime:<25}{name_col}  {fpath}")


if __name__ == "__main__":
    main()
