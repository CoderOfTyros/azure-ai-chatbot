import azure.functions as func
import json
import uuid, copy
import logging

from .openai_client import init_openai_client
from .cosmos_session_manager import CosmosSessionManager
from .utils import summarize, trim_conversation_by_tokens
from .retrieval import search_top_k_hybrid, format_sources_for_prompt
from .prompts import make_grounded_user_message
from .query_rewrite import rewrite_query

from .tools import TOOLS, TOOL_ROUTER


def _chat_with_tools(client, deployment_name, base_messages, session_id: str):
    """
    Minimal tool-calling loop:
      1) Ask model with tools advertised.
      2) If tool_calls present -> run tools -> append tool results -> ask model again.
    Returns: (assistant_message, image_urls_list)
    """
    working = list(base_messages)

    first = client.chat.completions.create(
        model=deployment_name,
        messages=working,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.2,
        max_tokens=700,
        top_p=1.0,
    )
    msg = first.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None)

    if not tool_calls:
        return msg, []

    # Append the assistant message EXACTLY with tool_calls
    assistant_with_tools = {
        "role": "assistant",
        "content": msg.content or None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ],
    }
    working.append(assistant_with_tools)

    image_urls = []
    # Execute tools and append their results
    for tc in tool_calls:
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments or "{}")
        except Exception:
            args = {}

        if name not in TOOL_ROUTER:
            result = {"error": f"tool {name} not allowed"}
        else:
            try:
                result = TOOL_ROUTER[name](session_id=session_id, **args)
            except Exception as e:
                logging.exception("Tool execution error")
                result = {"error": str(e)}

        try:
            for it in result.get("images", []):
                if it.get("url"):
                    image_urls.append(it["url"])
        except Exception:
            pass

        working.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": name,
            "content": json.dumps(result, ensure_ascii=False),
        })

    second = client.chat.completions.create(
        model=deployment_name,
        messages=working,
        temperature=0.2,
        max_tokens=700,
        top_p=1.0,
    )
    return second.choices[0].message, image_urls


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        user_input = body.get("message")
        session_id = body.get("session_id") or str(uuid.uuid4())
        skip_session_save = body.get("skip_session_save", False)
        allow_image_tool = body.get("allow_image_tool", True)

        if not user_input:
            return func.HttpResponse("Missing 'message' field.", status_code=400)

        session = CosmosSessionManager(session_id)

        # Utility commands
        cmd = (user_input or "").strip().lower()
        if cmd == "clear":
            session.clear()
            return func.HttpResponse(
                json.dumps({"status": "Session cleared", "session_id": session_id}),
                status_code=200, mimetype="application/json"
            )
        if cmd == "restart":
            new_session_id = str(uuid.uuid4())
            CosmosSessionManager(new_session_id).save()
            return func.HttpResponse(
                json.dumps({"status": "New session started", "session_id": new_session_id}),
                status_code=200, mimetype="application/json"
            )
        if cmd == "history":
            history = session.messages or []
            return func.HttpResponse(
                json.dumps({"history": history, "session_id": session_id}),
                status_code=200, mimetype="application/json"
            )

        # System policy (kept concise; includes tool usage guidance)
        system_prompt = (
    "You are a storytelling assistant specialized in retrieving and narrating stories "
    "from the knowledge base. Always base your answers strictly on the provided Sources "
    "when responding to questions about stories. "
    "If the user greets you (e.g., 'hello', 'hi', 'how are you'), respond politely with a short greeting "
    "but do not create new information outside the knowledge base. "
    "For all other unrelated questions, reply exactly with: "
    "'I can only answer questions related to the stories in the knowledge base.' "
    "If the user asks for an image, only generate it if the image request is directly related "
    "to the knowledge base content (e.g., a character, place, or event mentioned in the stories). "
    "When generating such an image request, expand the query into a detailed visual description "
    "that can be passed to the image generation function. "
    "If the user asks for an image unrelated to the knowledge base, reply exactly with: "
    "'I can only generate images related to the stories in the knowledge base.'"
    "If the user asks for an image and the request is related to the knowledge base, you MUST call the tool 'tool_generate_image'. Do not answer with text alone."
        )

        # Build conversation with session memory
        conversation = [{"role": "system", "content": system_prompt}]
        if session.messages:
            conversation += session.messages

        client, deployment_name = init_openai_client()

        # Query rewrite (robust fallback)
        try:
            search_query = rewrite_query(client, deployment_name, conversation, user_input)
        except Exception:
            search_query = user_input

        # RAG
        passages = search_top_k_hybrid(search_query, k=5)
        sources_formatted = format_sources_for_prompt(passages)
        grounded_user_msg = make_grounded_user_message(user_input, sources_formatted)

        conversation.append({"role": "user", "content": user_input})
        conversation_with_retrieved_sources = copy.deepcopy(conversation)
        conversation_with_retrieved_sources.append(grounded_user_msg)

        # Housekeeping for storage conversation
        conversation = summarize(conversation, client, deployment_name)
        conversation = trim_conversation_by_tokens(
            conversation=conversation,
            max_tokens=8192,
            model=deployment_name,
            safety_margin=500,
        )

        # Tool vs no-tool path
        if allow_image_tool:
            assistant_msg, image_urls = _chat_with_tools(
                client, deployment_name, conversation_with_retrieved_sources, session_id
            )
            reply = (assistant_msg.content or "").strip()
        else:
            tool_free_resp = client.chat.completions.create(
                model=deployment_name,
                messages=conversation_with_retrieved_sources,
                temperature=0.2,
                max_tokens=700,
                top_p=1.0,
            )
            reply = (tool_free_resp.choices[0].message.content or "").strip()
            image_urls = []

        # Persist only user/assistant roles
        conversation.append({"role": "assistant", "content": reply})
        if not skip_session_save:
            to_save = [m for m in conversation if m.get("role") in ("user", "assistant")]
            session.messages = to_save
            session.save()

        logging.info(f"Reply being returned to client: {reply}")

        return func.HttpResponse(
            json.dumps({"reply": reply, "session_id": session_id, "images": image_urls}, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("Function error:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
