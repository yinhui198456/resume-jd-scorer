# Findings

## Initial checks

- `graphify` was not available before installation.
- `uv` is available at `/root/.local/bin/uv`.
- Graphify official package is `graphifyy`; CLI command is `graphify`.
- Installed `graphifyy[chinese]` to support Chinese text segmentation.
- Workspace has many existing uncommitted changes, including `daily-ai-digest` source/config/test files.

## Pilot results

- Full staging scan found 39 code files and 17 doc-like files, but Graphify required an LLM API key for semantic extraction of docs.
- Code/config staging still counted YAML/TOML/service files as doc-like files, so it also required an LLM API key.
- Final code-only staging included Python and shell files only.
- Code-only extraction succeeded and wrote `daily-ai-digest/output/graphify-pilot/graphify-out/graph.json`.
- Generated graph size: 214 nodes, 614 raw edges.
- Generated HTML tree: `daily-ai-digest/output/graphify-pilot/graphify-out/GRAPH_TREE.html`.

## Full extraction results

- DashScope OpenAI-compatible endpoint was available from `/root/.hermes/.env`.
- `/v1/models` returned `qwen3-coder-plus`; this was used as the Graphify backend model.
- Required extra dependency was missing initially; fixed by reinstalling Graphify as `graphifyy[openai,chinese]`.
- Full extraction succeeded against the filtered staging directory:
  - 39 code files
  - 17 doc/config files
  - 264 nodes
  - 526 edges
  - 38 communities
- Output directory: `daily-ai-digest/output/graphify-pilot-full/graphify-out/`.
- Generated:
  - `graph.json`
  - `graph.html`
  - `GRAPH_TREE.html`
  - `GRAPH_REPORT.md`
- Graph diagnostics reported 0 dangling endpoints and 0 duplicate edges.

## Refresh workflow

- Added `daily-ai-digest/scripts/graphify_refresh.sh`.
- The script builds a temporary staging directory and excludes:
  - `.git`
  - `.venv`
  - `.pytest_cache`
  - `data`
  - `output`
  - `__pycache__`
  - `*.pyc`
- The script runs:
  - `graphify extract`
  - `graphify cluster-only`
  - `graphify tree`
  - mobile summary generation
- Added `tests/unit/test_graphify_refresh.py` to verify runtime directories are excluded and `MOBILE_SUMMARY.md` is produced.
- Real refresh completed and produced `daily-ai-digest/output/graphify-pilot-full/MOBILE_SUMMARY.md`.

## Daily digest quality follow-up

- Existing implementation already covers the two-section model:
  - `重点资讯`
  - `生产力项目`
- Existing tests cover 15 generated items, removal of candidate pool rendering, practice/productivity filtering, and excluding legal/safety/materially irrelevant practice items.
- Added missing protection for same-product version-title clustering outside GitHub release URLs.
- Added explicit test that GitHub repository search uses `pushed_at` as the item timestamp, preventing old created projects with recent pushes from being treated as 2024 news.

## Query checks

- `render_feishu_post()` was found at `src/digest/generate/render.py`.
- Graphify identified direct test callers:
  - `test_feishu_post_is_compact_and_uses_one_link()`
  - `test_feishu_post_renders_productivity_section()`
  - `test_feishu_post_keeps_fifteen_items_visible_in_compact_rows()`
- This is useful for quick test-impact discovery.
- Full graph query surfaced:
  - `Sources Configuration`
  - `Filters Configuration`
  - `Schedule Configuration`
  - `Topics Configuration`
  - `Tier 1 Sources`
  - `Tier 2 Sources`
  - `Feishu Delivery`
  - `run_daily`
- This confirms the full extraction is materially better than code-only for this project.

## Limitations

- Full graph source paths are mostly project-relative in query output, but extraction still ran from a temporary filtered staging directory.
- Some inferred edges should be treated as suggestions, not facts, until verified against code.
- Cost estimate printed by Graphify is backend-generic and not authoritative for DashScope billing.

## Safety decisions

- Do not run `graphify install --project --platform codex` during the pilot because it can modify project instruction files such as `AGENTS.md`.
- Generate graph output only, then review usefulness before enabling always-on agent integration.
- Keep Obsidian out of this phase because `OBSIDIAN_VAULT_PATH` is not configured.
- Use temporary staging under `/tmp` to exclude `.venv`, `data`, `output`, caches, and generated files.

## Evaluation questions

- Does the report identify the daily digest pipeline stages?
- Does it expose config-to-code relationships?
- Does it help answer impact questions faster than `rg` plus manual inspection?
- Is the output small and stable enough to keep in the project, or should it remain generated/ignored?
