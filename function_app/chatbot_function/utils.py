import tiktoken
import re


def summarize(conversation, client, model, num_to_summarize=5):
    """
    Summarize the oldest messages in a conversation if it exceeds a length threshold.

    Args:
        conversation (list): Full conversation list including system prompt.
        client (AzureOpenAI): OpenAI client.
        model (str): OpenAI deployment name.
        num_to_summarize (int): Number of old messages to summarize.

    Returns:
        list: Trimmed and/or summarized conversation.
    """

    if len(conversation) <= 1 + num_to_summarize * 2:
        return conversation  # not long enough to summarize

    system_prompt = conversation[0]

    # get oldest N messages (excluding system prompt)
    old_history = conversation[1:1 + num_to_summarize]
    recent_messages = conversation[1 + num_to_summarize:]

    summary_prompt = [
        {"role": "system", "content": "Summarize the following chat history briefly:"},
        {"role": "user", "content": "\n".join([m["content"] for m in old_history if m.get("content")])}
    ]

    try:
        summary_response = client.chat.completions.create(
            model=model,
            messages=summary_prompt,
            temperature=0.3
        )

        summary_text = summary_response.choices[0].message.content.strip()

        return [
            system_prompt,
            {"role": "system", "content": f"Summary of prior conversation: {summary_text}"},
            *recent_messages
        ]

    except Exception as e:
        print(f"Summarization failed: {e}")
        return [system_prompt] + recent_messages



def count_tokens(messages, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = 0
    for message in messages:
        tokens += 4 
        for key, value in message.items():
            tokens += len(encoding.encode(value))
    tokens += 2  
    return tokens

def trim_conversation_by_tokens(conversation, max_tokens=8192, model="gpt-4", safety_margin=500):
    """
    Simple token trimming:
    - Keeps system prompt (index 0)
    - Keeps as many recent messages as fit within budget
    - Discards everything else (summary included)
    """
    if not conversation:
        return []

    system_prompt = conversation[0]
    allowed_tokens = max_tokens - safety_margin
    total_tokens = count_tokens([system_prompt])

    trimmed = []
    for msg in reversed(conversation[1:]):
        msg_tokens = count_tokens([msg])
        if total_tokens + msg_tokens <= allowed_tokens:
            trimmed.insert(0, msg)
            total_tokens += msg_tokens
        else:
            break

    return [system_prompt] + trimmed

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t\f\v]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = "".join(ch for ch in t if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return t.strip()