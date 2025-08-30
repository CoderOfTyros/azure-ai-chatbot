# function_app/chatbot_function/prompts.py
from typing import Dict

GROUNDED_PROMPT = """
You are a friendly assistant.

Decision rule:
- If the Sources below clearly contain relevant facts that answer the Query, answer ONLY using those facts. Do not add outside knowledge. Include a short "Sources:" line listing the source titles you used.
- If the Sources are irrelevant or insufficient to answer the Query, say "Not found in knowledge base." and then answer using your general knowledge. When you use outside knowledge, DO NOT invent citations and omit the "Sources:" line.

Formatting:
- Be concise and use bullet points.
- Never invent facts.

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
