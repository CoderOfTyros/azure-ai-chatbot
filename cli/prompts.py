from typing import Dict

GROUNDED_PROMPT = """
Decision rule:
- If the Sources below contain relevant facts that answer the Query, answer using those facts.
- If the Query asks for interpretation, opinion, themes, character analysis, or discussion ABOUT the stories in the Sources, provide thoughtful commentary grounded in the Sources (paraphrase, quote short snippets, and tie claims back to them).
- Do NOT invent facts that contradict the Sources.
- Only when the Query is clearly unrelated to the stories (not about their plots, characters, style, or themes), say you can only discuss the provided stories.

Formatting:
- Be concise and natural.
- End with a short "Sources:" line listing the story titles you drew from.

Query:
{query}

Sources:
{sources}
""".strip()


def make_grounded_user_message(query: str, sources_formatted: str) -> Dict[str, str]:
    return {
        "role": "user",
        "content": GROUNDED_PROMPT.format(query=str(query), sources=str(sources_formatted)),
    }
