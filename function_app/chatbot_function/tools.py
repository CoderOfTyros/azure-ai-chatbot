import time
from typing import Dict, Any, Optional
import os, requests, logging
# Reuse your existing components
from .openai_client import init_openai_client
from .retrieval import search_top_k_hybrid, format_sources_for_prompt
from .prompts import make_grounded_user_message
from .query_rewrite import rewrite_query
from .utils import summarize, trim_conversation_by_tokens




# DALLE helper 
endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
key = os.environ.get("AZURE_OPENAI_KEY")
deployment = os.environ.get("AZURE_OPENAI_DALLE_DEPLOYMENT")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

def generate_image(prompt: str, size="1024x1024"):
    # DALL-E deployment path
    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/images/generations?api-version={api_version}"
    headers = {"api-key": key, "Content-Type": "application/json"}
    payload = {"prompt": prompt, "size": size, "n": 1}

    response = requests.post(url, headers=headers, json=payload)

    if not response.ok:
        logging.error(f"Image API error {response.status_code}: {response.text}")

    response.raise_for_status()
    data = response.json()

    return data["data"][0].get("url") or data["data"][0].get("b64_json")

def sanitize_prompt(user_prompt: str) -> str:
    return (
        "Create a safe, family-friendly artistic illustration based on this request: "
        f"{user_prompt}"
    )



_IMAGE_POLICY = (
    "You ONLY generate images related to the knowledge base stories.\n"
    "If unrelated, reply EXACTLY with: 'I can only generate images related to the stories in the knowledge base.'\n"
    "If related, output a SHORT, family-friendly, concrete visual description (composition, characters, scene, lighting). "
    "Do not add disclaimers or extra text."
)

def _expand_prompt_via_kb(user_prompt: str) -> Optional[str]:
    """Return a KB-grounded visual description or None if unrelated."""
    client, deployment = init_openai_client()
    convo = [{"role": "system", "content": _IMAGE_POLICY}]

    # Rewrite -> retrieve -> grounded user msg
    try:
        q = rewrite_query(client, deployment, convo, user_prompt)
    except Exception:
        q = user_prompt

    hits = search_top_k_hybrid(q, k=5)
    if not hits:
        return None

    sources = format_sources_for_prompt(hits)
    grounded = make_grounded_user_message(user_prompt, sources)

    convo.append({"role": "user", "content": user_prompt})
    convo2 = list(convo) + [grounded]

    # housekeeping
    convo2 = summarize(convo2, client, deployment)
    convo2 = trim_conversation_by_tokens(convo2, max_tokens=8192, model=deployment, safety_margin=500)

    # ask for final visual description
    resp = client.chat.completions.create(
        model=deployment,
        messages=convo2,
        temperature=0.2,
        max_tokens=700,
        top_p=1.0,
    )
    desc = (resp.choices[0].message.content or "").strip()
    refusal = "I can only generate images related to the stories in the knowledge base."
    if not desc or refusal in desc:
        return None
    return desc


def _normalize_image_result(result: Any, prompt: str, size: str, expanded: Optional[str]) -> Dict[str, Any]:
    images = []
    if isinstance(result, str):
        images = [{"url": result}]
    elif isinstance(result, dict):
        if "url" in result:
            images = [{"url": result["url"]}]
        elif "data" in result and isinstance(result["data"], list):
            images = [{"url": it.get("url")} for it in result["data"] if it.get("url")]
    return {
        "prompt": prompt,
        "expanded_description": expanded or prompt,
        "images": images,
        "size": size,
    }


def tool_generate_image(
    prompt: str,
    size: str = "1024x1024",
    session_id: Optional[str] = None,  # not used here but kept for API symmetry
) -> Dict[str, Any]:
    """
    In-process image generation:
      - KB-check + visual description via chat
      - DALLE generation via your existing helper
    """
    # 1) KB gate + expansion
    expanded = _expand_prompt_via_kb(prompt)
    if expanded is None:
        return {"error": "I can only generate images related to the stories in the knowledge base."}

    # 2) Call DALLE with light backoff around your helper (covers transient 429s)
    last_err = None
    for attempt in range(4):
        try:
            result = generate_image(prompt=expanded, size=size)
            return _normalize_image_result(result, prompt, size, expanded)
        except Exception as e:
            last_err = e
            # small exponential backoff
            time.sleep(1.0 * (2 ** attempt))

    logging.exception("Image generation failed after retries", exc_info=last_err)
    return {"error": f"image generation failed: {last_err}", "prompt": prompt, "size": size}


# ---- Tool schema advertised to the model ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tool_generate_image",
            "description": "Generate an image only if related to the knowledge base stories; returns image URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User's image request text."},
                    "size": {
                        "type": "string",
                        "enum": ["256x256", "512x512", "1024x1024"],
                        "default": "1024x1024"
                    }
                },
                "required": ["prompt"]
            }
        },
    },
]

# Strict allowlist
TOOL_ROUTER = {
    "tool_generate_image": tool_generate_image,
}
