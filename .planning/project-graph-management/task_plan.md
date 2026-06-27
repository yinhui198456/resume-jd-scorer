# Project graph management pilot

## Goal

Validate whether Graphify is useful for managing project structure and dependency context in `/opt/personal-agent-workspace`, starting with `daily-ai-digest` only.

## Scope

- Project: `/opt/personal-agent-workspace/daily-ai-digest`
- Output: project-local Graphify output only
- Excluded: Obsidian vault writes, global project graph, business code changes, data cleanup

## Phases

### Phase 1: Prepare

- [x] Confirm workspace write rules
- [x] Confirm Graphify is not already installed
- [x] Install Graphify CLI with Chinese text support
- [x] Avoid modifying existing dirty business files

### Phase 2: Generate pilot graph

- [x] Run Graphify against `daily-ai-digest`
- [x] Keep output isolated under Graphify output directory
- [x] Verify expected output files exist
- [x] Run full docs/config extraction with OpenAI-compatible DashScope backend
- [x] Generate `GRAPH_REPORT.md`, `graph.html`, and `GRAPH_TREE.html`

### Phase 3: Review usefulness

- [x] Inspect generated graph/query behavior
- [x] Identify whether it captures source, filter, generation, rendering, delivery, and timer relationships
- [x] Decide whether to install project-level Codex skill later

### Phase 4: Handoff

- [x] Summarize output paths
- [x] Summarize risks and recommended next step

### Phase 5: Refresh workflow

- [x] Add `scripts/graphify_refresh.sh`
- [x] Add TDD coverage for staging excludes and mobile summary generation
- [x] Generate `MOBILE_SUMMARY.md`
- [x] Run real Graphify refresh once

## Non-goals

- Do not modify `AGENTS.md` or existing source files during this pilot.
- Do not write to Obsidian vault.
- Do not scan all projects in `/opt/personal-agent-workspace`.

## Decision

Do not install the Codex Graphify skill yet. The graph output is useful, but project-level installation would modify `AGENTS.md`; defer that until the current dirty worktree is cleaned or explicitly approved.
