#!/usr/bin/env bash
set -euo pipefail
cd /opt/personal-agent-workspace/daily-ai-digest
.venv/bin/python -c 'from pathlib import Path; from digest.config import load_config; load_config(Path.cwd()); print("config: valid")'
