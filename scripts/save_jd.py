#!/usr/bin/env python3
"""JD 持久化模块。

保存最近使用的 JD 到本地文件，支持跨会话复用。
数据存储在 <skill_dir>/data/current_jd.json。

用法：
    # 保存 JD
    python3 save_jd.py save "JD 文本内容" [--source file:xxx.pdf]

    # 加载 JD
    python3 save_jd.py load

    # 检查是否有保存的 JD
    python3 save_jd.py has
"""

import json
import os
import sys
import datetime

# 数据目录（相对于脚本所在目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")


def _get_jd_file() -> str:
    """动态获取 JD 文件路径（支持测试时修改 DATA_DIR）。"""
    return os.path.join(DATA_DIR, "current_jd.json")


def _ensure_data_dir():
    """确保数据目录存在。"""
    os.makedirs(DATA_DIR, exist_ok=True)


def save_jd(jd_text: str, source: str = "user_input") -> dict:
    """保存 JD 到 current_jd.json。

    Args:
        jd_text: JD 文本内容
        source: 来源标识，如 "file:ai_infra.pdf" 或 "user_input"

    Returns:
        {"success": bool, "message": str}
    """
    if not jd_text or not jd_text.strip():
        return {"success": False, "message": "JD 文本为空"}

    _ensure_data_dir()

    # 处理 source：如果是文件路径，提取文件名
    if source.startswith("/") or source.startswith("./"):
        source = f"file:{os.path.basename(source)}"

    record = {
        "jd_text": jd_text.strip(),
        "saved_at": datetime.datetime.now().isoformat(),
        "source": source,
        "char_count": len(jd_text.strip()),
    }

    try:
        with open(_get_jd_file(), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return {"success": True, "message": f"JD 已保存（{record['char_count']} 字符）"}
    except Exception as e:
        return {"success": False, "message": f"保存失败: {e}"}


def load_jd() -> dict | None:
    """加载最近保存的 JD。

    Returns:
        包含 jd_text/saved_at/source 的 dict，或 None（未保存/文件损坏）
    """
    jd_file = _get_jd_file()
    if not os.path.isfile(jd_file):
        return None

    try:
        with open(jd_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 验证必要字段
        if "jd_text" not in data:
            return None
        return data
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def has_jd() -> bool:
    """检查是否有已保存的 JD。"""
    return load_jd() is not None


def main():
    if len(sys.argv) < 2:
        print("用法：python3 save_jd.py <save|load|has> [参数]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 3:
            print("错误：请提供 JD 文本", file=sys.stderr)
            sys.exit(1)

        jd_text = sys.argv[2]
        source = sys.argv[3] if len(sys.argv) > 3 else "cli"

        result = save_jd(jd_text, source)
        print(json.dumps(result, ensure_ascii=False))

        if not result["success"]:
            sys.exit(1)

    elif command == "load":
        data = load_jd()
        if data is None:
            print("未找到已保存的 JD", file=sys.stderr)
            sys.exit(1)
        print(data["jd_text"])

    elif command == "has":
        if has_jd():
            data = load_jd()
            info = f"已保存 | {data['source']} | {data['saved_at'][:19]} | {data['char_count']} 字符"
            print(info)
        else:
            print("未保存 JD")

    else:
        print(f"未知命令: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
