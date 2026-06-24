from types import SimpleNamespace

import pytest

from digest.generate.common import fallback_generation, parse_generation
from digest.generate.minimax import MiniMaxGenerator


class FakeCompletions:
    def __init__(self):
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        message = SimpleNamespace(content='{"chinese_title":"MCP 更新","summary":"发布新版本","why_it_matters":"影响工具集成"}')
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_minimax_generator_uses_configured_model():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    generator = MiniMaxGenerator("key", "https://api.minimaxi.com/v1/", "MiniMax-M3", client=client)

    result = generator.generate_text("MCP release")

    assert completions.request["model"] == "MiniMax-M3"
    assert result["chinese_title"] == "MCP 更新"
    system_prompt = completions.request["messages"][0]["content"]
    assert "100" in system_prompt
    assert "characters" in system_prompt
    assert "complete" in system_prompt.casefold()


def test_parse_generation_rejects_non_json():
    with pytest.raises(ValueError, match="invalid generation response"):
        parse_generation("not-json")


def test_parse_generation_accepts_minimax_think_prefix():
    result = parse_generation(
        '<think>reasoning</think>\n'
        '```json\n'
        '{"chinese_title":"MCP 更新","summary":"发布新版本",'
        '"why_it_matters":"影响工具集成"}\n'
        '```'
    )

    assert result["chinese_title"] == "MCP 更新"


def test_fallback_marks_english_translation_pending():
    result = fallback_generation("Codex update", "New MCP support", "en")
    assert result["translation_status"] == "pending"
