from pathlib import Path

import pytest

from digest.config import load_config


def write_configs(root: Path, filters: str = "{}\n") -> None:
    config_dir = root / "configs"
    config_dir.mkdir()
    (config_dir / "sources.yml").write_text("{}\n", encoding="utf-8")
    (config_dir / "filters.yml").write_text(filters, encoding="utf-8")
    (config_dir / "topics.yml").write_text("{}\n", encoding="utf-8")
    (config_dir / "schedule.yml").write_text("{}\n", encoding="utf-8")


def set_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MINIMAX_MODEL", "MiniMax-M3")
    monkeypatch.setenv("CTI_FEISHU_APP_ID", "cli_codex")
    monkeypatch.setenv("CTI_FEISHU_APP_SECRET", "codex-secret")
    monkeypatch.setenv("DAILY_AI_DIGEST_FEISHU_CHAT_ID", "oc_current_group")
    monkeypatch.setenv("FEISHU_APP_ID", "cli_wrong_legacy")
    monkeypatch.setenv("FEISHU_APP_SECRET", "wrong-legacy-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "oc_wrong_legacy")


def test_config_loads_shared_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    write_configs(tmp_path)
    set_required_environment(monkeypatch)

    config = load_config(tmp_path)

    assert config.minimax_model == "MiniMax-M3"
    assert config.feishu_app_id == "cli_codex"
    assert config.feishu_chat_id == "oc_current_group"


def test_config_rejects_weights_that_do_not_sum_to_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    write_configs(tmp_path, "weights: {source_trust: 0.4, recency: 0.4}\n")
    set_required_environment(monkeypatch)

    with pytest.raises(ValueError, match="filter weights must sum to 1.0"):
        load_config(tmp_path)
