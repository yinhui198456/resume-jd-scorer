#!/usr/bin/env bash
set -euo pipefail

# CI / 本地测试入口脚本
# 用法：./run_tests.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "==> 安装依赖（如已安装则跳过）"
pip install -q -r requirements.txt 2>/dev/null || true

echo "==> 运行 Skill 工具脚本测试"
pytest test_parse.py test_save_jd.py -v

echo "==> 运行 scorer 单元测试"
pytest test_scorer.py -v

echo "==> 运行 API 单元测试"
pytest tests/ -v

echo "==> 全部测试通过"
