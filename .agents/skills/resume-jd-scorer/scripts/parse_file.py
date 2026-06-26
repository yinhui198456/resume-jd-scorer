#!/usr/bin/env python3
"""解析简历文件为纯文本。

支持格式：
- PDF（含 .pdf 和 magic 检测为 PDF 的文件）
- DOCX（含 .docx 和 magic 检测为 ZIP/DOCX 的文件）
- TXT（纯文本）
- PNG / JPG / WEBP（OCR 识别，Tesseract + pytesseract）

用法：
    python3 parse_file.py <文件路径>

输出：提取的文本内容（stdout），用于后续 LLM 评估。
"""

import os
import re
import sys

import magic
from PIL import Image
import pytesseract
from docx import Document
from PyPDF2 import PdfReader

# ---- 文件类型检测（magic bytes，不依赖扩展名） ----

MIME_TO_FORMAT = {
    "application/pdf": "pdf",
    "application/zip": "docx",    # .docx 本质是 ZIP
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}

OCR_THRESHOLD = 180  # 二值化阈值，灰度值 > 此值视为白色


def detect_mime_type(path: str) -> str:
    """使用 python-magic 检测文件真实 MIME type。"""
    return magic.from_file(path, mime=True)


# ---- 候选人姓名提取 ----

_NAME_PATTERN = re.compile(r'(?:姓名|名)\s*[:：]\s*([一-鿿]{1,4})')


def extract_candidate_name(text: str) -> str | None:
    """从简历文本中提取候选人姓名。

    支持模式：
    - 姓名:王洁玉 / 姓名：张三（标准格式）
    - 名 ：袁永泉（OCR 噪声前缀 + 截断标签）
    - 姓名\\n：王洁玉（OCR 断行）

    返回：姓名字符串，未找到返回 None。
    """
    if not text or not text.strip():
        return None

    # 先尝试单行匹配（覆盖 90%+ 场景）
    for line in text.split("\n"):
        m = _NAME_PATTERN.search(line)
        if m:
            return m.group(1)

    # 再尝试跨行匹配（OCR 断行场景）
    for i in range(len(text) - 1):
        pair = text[i:i+2]
        if pair == "\n:" or pair == "\n：":
            # 往前找"姓名"或"名"，往后找中文名字
            prefix = text[:i].rstrip()
            suffix = text[i+2:].lstrip()
            if re.search(r'(?:姓名|名)\s*$', prefix):
                m = re.match(r'([一-鿿]{1,4})', suffix)
                if m:
                    return m.group(1)

    return None


# ---- 各格式解析器 ----

def parse_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def parse_pdf(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def parse_image(path: str) -> str:
    """使用 Tesseract OCR 识别图片文字（中英文）。

    预处理：灰度化 + 二值化，提升识别率。
    """
    img = Image.open(path).convert("L")
    # 纯 Pillow 二值化，无需 numpy
    img = img.point(lambda x: 255 if x > OCR_THRESHOLD else 0, mode="1").convert("L")
    return pytesseract.image_to_string(img, lang="chi_sim+eng")


# ---- 主流程 ----

def main():
    if len(sys.argv) < 2:
        print("错误：请指定文件路径", file=sys.stderr)
        print("用法：python3 parse_file.py <文件路径>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"错误：文件不存在 — {path}", file=sys.stderr)
        sys.exit(1)

    # 第一步：用 magic bytes 检测真实格式
    mime = detect_mime_type(path)
    fmt = MIME_TO_FORMAT.get(mime)

    if fmt is None:
        print(f"错误：不支持的文件类型 — {mime}（文件: {path}）", file=sys.stderr)
        sys.exit(1)

    try:
        parsers = {
            "txt": parse_txt,
            "docx": parse_docx,
            "pdf": parse_pdf,
            "image": parse_image,
        }
        text = parsers[fmt](path)

        if not text.strip():
            print("错误：文件内容为空", file=sys.stderr)
            sys.exit(1)

        print(text)

    except Exception as e:
        print(f"错误：文件解析失败 — {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
