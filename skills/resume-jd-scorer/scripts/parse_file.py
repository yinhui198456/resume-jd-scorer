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

# 水印/乱码模式（PDF解析常见噪声）
_WATERMARK_PATTERN = re.compile(r'[0-9a-f]{16,}HF[0-9a-zA-Z]{10,}WOelmv7WPxBh')
import sys

import magic
from PIL import Image
import pytesseract
from docx import Document
import fitz  # PyMuPDF

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
# 常见姓名：2–4 个汉字，排除明显不是人名的词
_NAME_CANDIDATE_PATTERN = re.compile(r'^\s*([一-鿿]{2,4})\s*$')
# 简历标题中“XXX 个人简历”的 XXX
_RESUME_TITLE_PATTERN = re.compile(r'^\s*([一-鿿]{2,4})\s*(?:个人)?简历')
# 联系方式附近的上下文线索
_CONTACT_CONTEXT_PATTERN = re.compile(
    r'(?:电话|手机|邮箱|邮件|年龄|性别|求职岗位|意向岗位)[：:]\s*[^\n]+',
    re.IGNORECASE,
)


def _looks_like_name(token: str) -> bool:
    """粗略判断一个 2–4 字中文 token 是否像人名。

    排除常见简历标题、岗位、状态等噪声词。
    """
    noise = {
        '个人信息', '工作经历', '项目经历', '项目经验', '教育背景', '专业技能',
        '个人技能', '技能特长', '技能优势', '个人优势', '自我评价', '求职意向',
        '意向岗位', '工作年限', '工作经验', '当前状态', '离职', '在职',
        '男', '女', '汉族', '本科', '大专', '硕士', '博士',
        '电话', '手机', '邮箱', '邮件', '年龄', '姓名', '性别',
        '籍贯', '政治面貌', '联系方式', '个人博客', '求职岗位',
        '一年以上', '二年以上', '三年以上', '四年以上', '五年以上',
    }
    if token in noise:
        return False
    # 排除纯数字或含字母
    if re.search(r'[a-zA-Z0-9]', token):
        return False
    return True


def extract_candidate_name(text: str) -> str | None:
    """从简历文本中提取候选人姓名。

    支持模式：
    - 姓名：张三 / 姓名 张三（标准格式）
    - XXX 个人简历 / XXX简历（标题格式）
    - 联系方式附近的无标签姓名（如邮箱下方的“黄澳博”）
    - OCR 断行导致的“姓\n名\n：张三”

    返回：姓名字符串，未找到返回 None。
    """
    if not text or not text.strip():
        return None

    lines = [line.strip() for line in text.split("\n")]

    # 1. 标准带标签格式（单行）
    for line in lines:
        m = _NAME_PATTERN.search(line)
        if m:
            return m.group(1)

    # 2. 跨行标签格式（OCR 把“姓名”和“：张三”断开了）
    for i, line in enumerate(lines):
        if re.search(r'(?:姓名|名)\s*$', line):
            # 往后找 3 行内的中文名
            for j in range(i + 1, min(i + 4, len(lines))):
                # 可能是 “：张三” 或 “张三”
                m = re.match(r'[:：]?\s*([一-鿿]{1,4})', lines[j])
                if m and _looks_like_name(m.group(1)):
                    return m.group(1)

    # 3. 简历标题格式：“黄澳博 个人简历”
    for line in lines[:20]:  # 只看前 20 行
        m = _RESUME_TITLE_PATTERN.search(line)
        if m:
            candidate = m.group(1)
            if _looks_like_name(candidate):
                return candidate

    # 4. 联系方式附近的无标签姓名
    # 策略：找到包含“电话/邮箱/年龄/求职岗位”的行，检查它前后 2 行内的 2–4 字中文
    for i, line in enumerate(lines):
        if _CONTACT_CONTEXT_PATTERN.search(line):
            for j in range(max(0, i - 2), min(len(lines), i + 3)):
                if j == i:
                    continue
                m = _NAME_CANDIDATE_PATTERN.match(lines[j])
                if m and _looks_like_name(m.group(1)):
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
    """使用 PyMuPDF 提取 PDF 文本。

    PyMuPDF 对复杂版式、分栏、中文 PDF 的提取质量优于 PyPDF2。
    """
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text()
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
    raw = pytesseract.image_to_string(img, lang="chi_sim+eng")
    return _WATERMARK_PATTERN.sub('', raw)


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


def parse_resume(path: str) -> dict:
    """Parse a resume file and return structured result.

    Returns:
        {"type": mime_type, "name": file_name, "text": extracted_text}
    Raises:
        ValueError: if file type unsupported or parsing fails.
    """
    import os

    if not os.path.isfile(path):
        raise ValueError(f"文件不存在 — {path}")

    mime = detect_mime_type(path)
    fmt = MIME_TO_FORMAT.get(mime)
    if fmt is None:
        raise ValueError(f"不支持的文件类型 — {mime}")

    parsers = {
        "txt": parse_txt,
        "docx": parse_docx,
        "pdf": parse_pdf,
        "image": parse_image,
    }
    text = parsers[fmt](path)
    if not text.strip():
        raise ValueError("文件内容为空")

    return {
        "type": mime,
        "name": os.path.basename(path),
        "text": text,
    }


if __name__ == "__main__":
    main()
