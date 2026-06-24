# Daily AI Digest

Single-user AI news pipeline. It starts at 08:45 Asia/Shanghai, persists recoverable stage checkpoints, generates Chinese summaries with the shared MiniMax configuration, and sends the result to the configured Feishu group.

## Local verification

```bash
.venv/bin/python -m pytest -v
scripts/validate_config.sh
```

Tests do not call MiniMax, GitHub, source websites, or Feishu. Live smoke commands require explicit operator approval; see `docs/operations.md`.
