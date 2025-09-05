import azure.functions as func
import json
import uuid
import logging

from .openai_client import init_openai_client
from .cosmos_session_manager import CosmosSessionManager
from .utils import summarize, trim_conversation_by_tokens

from .retrieval import search_top_k, format_sources_for_prompt
from .prompts import make_grounded_user_message


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        user_message = body.get("message")
        session_id = body.get("session_id") or str(uuid.uuid4())
        role = body.get("role", "")

        if not user_message:
            return func.HttpResponse("Missing 'message' field.", status_code=400)

        
        session = CosmosSessionManager(session_id)

        if user_message.lower() == "clear":
            session.clear()
            return func.HttpResponse(
                json.dumps({
                    "status": "Session cleared",
                    "session_id": session_id
                }),
                status_code=200,
                mimetype="application/json"
            )

        if user_message.lower() == "restart":
            new_session_id = str(uuid.uuid4())
            new_session = CosmosSessionManager(new_session_id)
            new_session.save()
            return func.HttpResponse(
                json.dumps({
                    "status": "New session started",
                    "session_id": new_session_id
                }),
                status_code=200,
                mimetype="application/json"
            )

        if user_message.lower() == "history":
            history = session.messages or []
            return func.HttpResponse(
                json.dumps({
                    "history": history,
                    "session_id": session_id
                }),
                status_code=200,
                mimetype="application/json"
            )

       
        system_prompt = f"You are a helpful assistant specialized in {role}." if role else "You are a helpful assistant."
        conversation = [{"role": "system", "content": system_prompt}]
        if session.messages:
            conversation += session.messages

        # ---- RAG (BM25) step: retrieve sources & ground the query ----
        passages = search_top_k(user_message, k=5)  # hotels sample expects 5
        sources_formatted = format_sources_for_prompt(passages)
        grounded_user_msg = make_grounded_user_message(user_message, sources_formatted)
        conversation.append(grounded_user_msg)
       

       
        client, deployment_name = init_openai_client()

        # Summarize if needed 
        conversation = summarize(conversation, client, deployment_name)

       
        conversation = trim_conversation_by_tokens(
            conversation=conversation,
            max_tokens=8192,
            model=deployment_name,
            safety_margin=500
        )

        
        response = client.chat.completions.create(
            model=deployment_name,
            messages=conversation,
            temperature=0.2, 
            max_tokens=4096,
            top_p=1.0,
        )

        reply = response.choices[0].message.content.strip()
        conversation.append({"role": "assistant", "content": reply})

        session.messages = conversation[1:]
        session.save()

        logging.info(f"Reply being returned to client: {reply}")

        return func.HttpResponse(
            json.dumps({"reply": reply, "session_id": session_id}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Function error:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
