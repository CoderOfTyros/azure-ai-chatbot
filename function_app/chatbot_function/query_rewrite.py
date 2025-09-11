from typing import List, Dict

REWRITE_PROMPT = """You will be given a chat history and the latest user prompt.
Rewrite the latest user prompt into a single, self-contained question/prompt that preserves context.
- Keep names, places, or references resolved (no pronouns like he/she/they/it).
- Do NOT add new information not present in the history.
Return only the rewritten question/prompt, nothing else.

Chat history (most recent last):
{history}

Latest user prompt:
{question}
"""

def collect_recent_history(messages: List[Dict], max_chars: int = 2000) -> str:
    # messages is a list of {"role": "...", "content": "..."}
    buf = []
    char_count = 0
    for m in messages[-12:]:  # last dozen turns is usually enough
        line = f"{m['role']}: {m['content']}"
        char_count += len(line)
        buf.append(line)
        if char_count > max_chars:
            break
    return "\n".join(buf[-12:])

def rewrite_query(client, model: str, messages: List[Dict], user_input: str) -> str:
    history = collect_recent_history(messages)
    prompt = REWRITE_PROMPT.format(history=history, question=user_input)
    out = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200,
    )
    rewritten = out.choices[0].message.content.strip()
    return rewritten or user_input
