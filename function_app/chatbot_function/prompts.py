# function_app/chatbot_function/prompts.py
from typing import Dict

GROUNDED_PROMPT = """
Decision rule:
- If the Sources below clearly contain relevant facts that answer the Query, answer ONLY using those facts. Include a short "Sources:" line listing the source titles you used.
- If the Sources are irrelevant or insufficient to answer the Query, answer using your general knowledge. Do NOT mention the knowledge base or sources, and do NOT fabricate citations.

Special cases:
- If the Query is a greeting or a meta-question about the assistant (e.g., "what's your role?", "who are you?", "what can you do?"), ignore Sources and answer directly based on the role assigned in the system instructions (your role). Do not mention the knowledge base or sources.

Formatting:
- Be concise and use bullet points when listing items.
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
