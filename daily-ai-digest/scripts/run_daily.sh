#!/usr/bin/env bash
set -euo pipefail
cd /opt/personal-agent-workspace/daily-ai-digest
exec .venv/bin/python -m digest.jobs.daily
