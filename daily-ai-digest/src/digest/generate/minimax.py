from openai import OpenAI

from digest.generate.common import parse_generation


class MiniMaxGenerator:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        client: object | None = None,
    ):
        self.client = client or OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120.0,
            max_retries=2,
        )
        self.model = model

    def generate_text(self, source_text: str) -> dict[str, str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate to concise Chinese. Preserve Agent, RAG, MCP, "
                        "Function Calling, Tool Calling, Evaluation, Observability, "
                        "Codex, and Claude Code in English. Write one complete, "
                        "explanatory summary within 100 Chinese characters. For "
                        "productivity/project items, explain what it is, why it is "
                        "worth mentioning now, what productivity it improves, and "
                        "its advantage or likely alternative. Do not focus on minor "
                        "patch details unless they change user-visible capability. "
                        "Return exactly one JSON "
                        "object with chinese_title, summary, and why_it_matters."
                    ),
                },
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
        return parse_generation(response.choices[0].message.content or "")
