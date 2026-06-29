from pathlib import Path

import yaml


def test_sources_include_codex_and_claude_code_skills_searches():
    sources = yaml.safe_load(Path("configs/sources.yml").read_text(encoding="utf-8"))
    search_sources = {
        source["id"]: source
        for source in sources["github_repository_search"]
    }

    for source_id in ("github-codex-skills", "github-claude-code-skills"):
        source = search_sources[source_id]
        assert source["tier"] == 2
        assert source["content_group"] == "github_projects"
        assert source["candidate_pool"] is True
        assert "pushed:>=2026-01-01" in source["query"]

    assert "topic:codex" in search_sources["github-codex-skills"]["query"]
    assert "topic:agent-skills" in search_sources["github-codex-skills"]["query"]
    assert "topic:claude-code" in search_sources["github-claude-code-skills"]["query"]
    assert "topic:agent-skills" in search_sources["github-claude-code-skills"]["query"]
