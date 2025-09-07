import azure.functions as func
import json
import uuid, os, copy
import logging

from .openai_client import init_openai_client
from .cosmos_session_manager import CosmosSessionManager
from .utils import summarize, trim_conversation_by_tokens

from .retrieval import search_top_k_hybrid, format_sources_for_prompt
from .prompts import make_grounded_user_message

from .query_rewrite import rewrite_query

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        user_input = body.get("message")
        session_id = body.get("session_id") or str(uuid.uuid4())
        role = body.get("role", "")

        if not user_input:
            return func.HttpResponse("Missing 'message' field.", status_code=400)

        
        session = CosmosSessionManager(session_id)

        if user_input.lower() == "clear":
            session.clear()
            return func.HttpResponse(
                json.dumps({
                    "status": "Session cleared",
                    "session_id": session_id
                }),
                status_code=200,
                mimetype="application/json"
            )

        if user_input.lower() == "restart":
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

        if user_input.lower() == "history":
            history = session.messages or []
            return func.HttpResponse(
                json.dumps({
                    "history": history,
                    "session_id": session_id
                }),
                status_code=200,
                mimetype="application/json"
            )

       
        # system_prompt = f"You are a helpful assistant specialized in {role}." if role else "You are a helpful assistant."
        system_prompt = (
                   "You are a helpful assistant. You must only answer using the provided Sources "
                   "about the stories in the knowledge base. If the question is unrelated or the "
                   "Sources are not relevant, reply: 'I can only answer questions related to the stories in the knowledge base.'")

        conversation = [{"role": "system", "content": system_prompt}]
        if session.messages:
            conversation += session.messages

        client, deployment_name = init_openai_client()
        
        try:
             search_query = rewrite_query(client, deployment_name, conversation, user_input)
          
        except Exception:
             search_query = user_input  

        # ----                  RAG step                     ----
        
        SEM_CFG = os.environ.get("AZURE_SEARCH_SEMANTIC_CONFIG")  
        passages = search_top_k_hybrid(search_query, k=5, semantic_config=SEM_CFG)
        sources_formatted = format_sources_for_prompt(passages)
        grounded_user_msg = make_grounded_user_message(user_input, sources_formatted)


        conversation.append({"role": "user","content": user_input})
       
        conversation_with_retrieved_sources = copy.deepcopy(conversation)
        conversation_with_retrieved_sources.append(grounded_user_msg)


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
            messages=conversation_with_retrieved_sources,
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
