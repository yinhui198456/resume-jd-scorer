# Findings

## Requirements

- Apply `configs/filters.yml` quotas before MiniMax generation and delivery.
- Persist source-level collection failures so a degraded checkpoint is actionable.
- Diagnose and, where locally fixable, resolve the actual source failures.
- Preserve historical run data and avoid duplicate delivery during repair.

## Current evidence

- Live run `20260623T134129+0800-492444e1` collected 64 raw items.
- Deduplication and filtering retained 47 items.
- Topic-overlap clustering produced 35 clusters and all 35 were generated and delivered.
- `filters.yml` defines quotas, but `run_daily()` currently does not read `config.filters["quotas"]` during selection.
- `_default_collector()` returns source failures, but the collect checkpoint stores only degraded status and count.
- Live per-source reproduction: `openai-codex-changelog` returned 50 items and
  `anthropic-news` returned 14 items.
- `openai-news` returned HTTP 403 from Cloudflare.
- All three GitHub release API calls returned HTTP 403 rate-limit errors because
  no authenticated `GITHUB_TOKEN` is available to the collector.
- The web research connector also returned a Cloudflare HTTP 403, so endpoint
  verification will use direct read-only HTTP probes against the official hosts.
- Official endpoint probes succeeded for `https://openai.com/news/rss.xml` and
  each configured repository's `releases.atom`; all returned parseable XML.
- `gh auth status` shows a local authenticated account, but coupling the service
  to interactive `gh` state is less robust than the public official Atom fallback.
- The design requires `score >= 0.70` in top stories, `score >= 0.55` in the
  candidate pool, maximum 10 in each, and deterministic tie-breaking.
- The design also requires partial source failures in runtime source-health state;
  `source_health.json` is named explicitly in the minimum runtime state.

## Technical decisions

| Decision | Rationale |
|---|---|
| Diagnose live sources individually | The existing checkpoint omitted failure details |
| Test selection and checkpoint output as observable behavior | Prevents regression without coupling tests to implementation internals |
| Use OpenAI RSS instead of its Cloudflare-protected HTML index | Official RSS is reachable and parseable by the service |
| Fall back from GitHub API rate-limit responses to official releases Atom | Preserves unauthenticated scheduled operation without coupling to `gh` login state |
| Persist per-run failures and latest `source_health.json` | Matches the design acceptance criteria and makes degraded status actionable |
