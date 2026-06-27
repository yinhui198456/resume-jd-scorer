#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${GRAPHIFY_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_ROOT="${GRAPHIFY_OUT_ROOT:-$PROJECT_ROOT/output/graphify-pilot-full}"
STAGING_DIR="${GRAPHIFY_STAGING_DIR:-/tmp/$(basename "$PROJECT_ROOT")-graphify-input}"
BACKEND="${GRAPHIFY_BACKEND:-openai}"
MODEL="${GRAPHIFY_MODEL:-qwen3-coder-plus}"
MAX_CONCURRENCY="${GRAPHIFY_MAX_CONCURRENCY:-1}"
API_TIMEOUT="${GRAPHIFY_API_TIMEOUT:-300}"
ENV_FILE="${GRAPHIFY_ENV_FILE:-/root/.hermes/.env}"

if ! command -v graphify >/dev/null 2>&1; then
  echo "graphify command not found. Install with: uv tool install \"graphifyy[openai,chinese]\"" >&2
  exit 127
fi

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  . "$ENV_FILE"
  set +a
fi

if [ -n "${DASHSCOPE_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  export OPENAI_API_KEY="$DASHSCOPE_API_KEY"
fi

if [ -n "${DASHSCOPE_BASE_URL:-}" ] && [ -z "${OPENAI_BASE_URL:-}" ]; then
  export OPENAI_BASE_URL="$DASHSCOPE_BASE_URL"
fi

if [ -z "${OPENAI_MODEL:-}" ]; then
  export OPENAI_MODEL="$MODEL"
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR" "$OUT_ROOT"

rsync -a \
  --exclude '.git/***' \
  --exclude '.venv/***' \
  --exclude '.pytest_cache/***' \
  --exclude 'data/***' \
  --exclude 'output/***' \
  --exclude '__pycache__/***' \
  --exclude '*.pyc' \
  "$PROJECT_ROOT/" "$STAGING_DIR/"

graphify extract "$STAGING_DIR" \
  --out "$OUT_ROOT" \
  --backend "$BACKEND" \
  --model "$MODEL" \
  --max-concurrency "$MAX_CONCURRENCY" \
  --api-timeout "$API_TIMEOUT"

graphify cluster-only "$OUT_ROOT" \
  --backend "$BACKEND" \
  --model "$MODEL" \
  --max-concurrency "$MAX_CONCURRENCY" \
  --batch-size "${GRAPHIFY_BATCH_SIZE:-20}"

graphify tree \
  --graph "$OUT_ROOT/graphify-out/graph.json" \
  --output "$OUT_ROOT/graphify-out/GRAPH_TREE.html" \
  --root "$STAGING_DIR" \
  --label "$(basename "$PROJECT_ROOT")"

python3 - "$OUT_ROOT/graphify-out/GRAPH_REPORT.md" "$OUT_ROOT/MOBILE_SUMMARY.md" <<'PY'
from pathlib import Path
import re
import sys

report = Path(sys.argv[1])
out = Path(sys.argv[2])
text = report.read_text(encoding="utf-8")

summary_match = re.search(r"## Summary\n(?P<body>.*?)(?:\n## |\Z)", text, re.S)
god_match = re.search(r"## God Nodes.*?\n(?P<body>.*?)(?:\n## |\Z)", text, re.S)
communities_match = re.search(r"## Community Hubs.*?\n(?P<body>.*?)(?:\n## |\Z)", text, re.S)

summary = ""
if summary_match:
    first = [line.strip() for line in summary_match.group("body").splitlines() if line.strip()]
    summary = first[0] if first else ""

god_nodes = []
if god_match:
    for line in god_match.group("body").splitlines():
        m = re.match(r"\d+\.\s+`([^`]+)`", line.strip())
        if m:
            god_nodes.append(m.group(1))
        if len(god_nodes) >= 5:
            break

communities = []
if communities_match:
    for line in communities_match.group("body").splitlines():
        m = re.search(r"\[\[_COMMUNITY_([^|\]]+)", line)
        if m:
            communities.append(m.group(1).replace("_", " "))
        if len(communities) >= 6:
            break

if not communities:
    for line in text.splitlines():
        m = re.match(r"### Community \d+ - \"(.+)\"", line.strip())
        if m:
            communities.append(m.group(1))
        if len(communities) >= 6:
            break

if not god_nodes:
    god_nodes = ["run_daily()", "PipelineDependencies", "AppConfig", "FeishuDelivery", "render_feishu_post()"]

if not communities:
    communities = [
        "Digest Pipeline Stages",
        "Application Configuration",
        "Content Collection",
        "Feishu Delivery System",
        "Digest Rendering",
        "Filtering and Scoring",
    ]

content = f"""# Graphify 移动端可读版

## 1. 有什么用

这不是给人从头读的长报告，而是项目地图。改代码前先查入口、影响面、相关测试和文档配置关系。

## 2. 图谱概况

{summary or "- 见 GRAPH_REPORT.md Summary"}

## 3. 核心入口

""" + "\n".join(f"- `{node}`" for node in god_nodes) + """

## 4. 主要模块

""" + "\n".join(f"- {name}" for name in communities) + """

## 5. 修改前怎么用

- 改飞书排版：查 `render_feishu_post()`
- 改资讯数量：查 `filters.yml`、`run_daily()`
- 改来源：查 `sources.yml`、collector
- 改分类：查 `topics.yml`、quality/filter
- 改定时：查 `schedule.yml`、deploy/service

## 6. 当前建议

保留 full graph 和本摘要。后续每次大改前先刷新图谱，再用 `graphify query` 或 `graphify affected` 查影响面。
"""

out.write_text(content, encoding="utf-8")
PY

echo "Graphify refresh complete:"
echo "  $OUT_ROOT/graphify-out/GRAPH_REPORT.md"
echo "  $OUT_ROOT/graphify-out/graph.html"
echo "  $OUT_ROOT/graphify-out/GRAPH_TREE.html"
echo "  $OUT_ROOT/MOBILE_SUMMARY.md"
