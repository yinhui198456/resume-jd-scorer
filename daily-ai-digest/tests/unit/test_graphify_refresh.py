import os
import subprocess
from pathlib import Path


def test_graphify_refresh_excludes_runtime_dirs_and_writes_mobile_summary(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "docs").mkdir()
    (project / "data").mkdir()
    (project / ".venv" / "lib").mkdir(parents=True)
    (project / ".pytest_cache").mkdir()
    (project / "output").mkdir()
    (project / "src" / "daily.py").write_text("def run_daily():\n    return True\n", encoding="utf-8")
    (project / "docs" / "source-policy.md").write_text("# Source Policy\n", encoding="utf-8")
    (project / "data" / "runtime.json").write_text("{}", encoding="utf-8")
    (project / ".venv" / "lib" / "ignored.py").write_text("def ignored(): pass\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "graphify.log"
    fake_graphify = fake_bin / "graphify"
    fake_graphify.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> "$GRAPHIFY_FAKE_LOG"
case "$1" in
  extract)
    staging="$2"
    out_root=""
    shift 2
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --out) out_root="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    test -f "$staging/src/daily.py"
    test -f "$staging/docs/source-policy.md"
    test ! -e "$staging/data/runtime.json"
    test ! -e "$staging/.venv/lib/ignored.py"
    mkdir -p "$out_root/graphify-out"
    printf '{"nodes":[{"id":"run_daily"}],"links":[{"source":"run_daily","target":"FeishuDelivery"}]}' > "$out_root/graphify-out/graph.json"
    printf '# Graph Report\\n\\n## Summary\\n- 1 nodes · 1 edges · 1 communities\\n\\n## God Nodes\\n1. `run_daily()` - 1 edges\\n\\n## Communities\\n### Community 0 - "Daily AI Digest Pipeline"\\n' > "$out_root/graphify-out/GRAPH_REPORT.md"
    ;;
  cluster-only)
    ;;
  tree)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    mkdir -p "$(dirname "$output")"
    printf '<html>tree</html>' > "$output"
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_graphify.chmod(0o755)

    out_root = tmp_path / "graphify-output"
    staging = tmp_path / "staging"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "GRAPHIFY_FAKE_LOG": str(log),
        "GRAPHIFY_PROJECT_ROOT": str(project),
        "GRAPHIFY_OUT_ROOT": str(out_root),
        "GRAPHIFY_STAGING_DIR": str(staging),
        "GRAPHIFY_BACKEND": "openai",
        "GRAPHIFY_MODEL": "test-model",
    }

    result = subprocess.run(
        ["bash", str(Path(__file__).parents[2] / "scripts" / "graphify_refresh.sh")],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    mobile = out_root / "MOBILE_SUMMARY.md"
    assert mobile.exists()
    text = mobile.read_text(encoding="utf-8")
    assert "移动端可读版" in text
    assert "run_daily()" in text
    assert "Daily AI Digest Pipeline" in text
    assert (out_root / "graphify-out" / "GRAPH_TREE.html").exists()
