# Operations

MiniMax configuration and `DAILY_AI_DIGEST_FEISHU_CHAT_ID` are loaded from
`/opt/personal-agent-workspace/.env`. Feishu Bot credentials are loaded directly
from `/root/.claude-to-im/config.env`; do not duplicate those secrets in this
project or reuse Hermes profile credentials.

Run a manual full pipeline with `scripts/run_daily.sh`. Retry a run with `.venv/bin/python -m digest.jobs.daily --run-id <existing-run-id> --force`.

OpenAI News is collected from its official RSS feed. GitHub Releases uses the
REST API and falls back to each repository's official `releases.atom` feed when
anonymous API rate limits return HTTP 403 or 429. Partial failures are recorded
under `data/state/runs/<run-id>/source_health.json` and mirrored to
`data/state/source_health.json`.

Normal digests are delivered as one compact Feishu rich-text Post through the
existing `Codex-学习助理` application: at most 8 top stories and 3 candidates,
with complete top-story summaries capped at 100 characters and one primary link per item.
Total-source fault digests continue to use plain text so recovery details remain
available even when no normal Post can be built.

Before enabling systemd, run the full test suite, `scripts/validate_config.sh`, and `systemd-analyze verify deploy/daily-ai-digest.service deploy/daily-ai-digest.timer`.

The following commands make real external calls and require explicit approval:

```bash
.venv/bin/python -m digest.jobs.daily --smoke-minimax
.venv/bin/python -m digest.jobs.daily --smoke-feishu --message "Daily AI Digest delivery test"
```

## Learning plan tracking

The learning-plan tracker records user-selected Daily AI Digest items into the Feishu spreadsheet `学习计划追踪 2026`, sheet `主任务`.

Preview only:

```bash
PYTHONPATH=src .venv/bin/python -m digest.jobs.learning_plan \
  --title "Graphify" \
  --summary "将代码和文档转为知识图谱。" \
  --url "https://github.com/safishamsi/graphify" \
  --source-date "2026-06-29" \
  --intent "感兴趣" \
  --stars 5154
```

Apply after user confirmation:

```bash
PYTHONPATH=src .venv/bin/python -m digest.jobs.learning_plan \
  --title "Graphify" \
  --summary "将代码和文档转为知识图谱。" \
  --url "https://github.com/safishamsi/graphify" \
  --source-date "2026-06-29" \
  --intent "感兴趣" \
  --stars 5154 \
  --apply
```

Rules:

- Never apply without explicit user confirmation.
- Do not record every digest item automatically.
- The tracker writes only columns A-I.
- Duplicate rows update notes/link only.
- Real write smoke tests require user approval.
