# cli/chatbot.py

from .openai_client import init_openai_client
from ..session.cosmos_session_manager import CosmosSessionManager
from .utils import summarize, trim_conversation_by_tokens
from .retrieval import search_top_k, format_sources_for_prompt
from .prompts import make_grounded_user_message

import re, uuid

def clean_session_id(text):
    return re.sub(r"[^\w\-]", "", text.strip())

def start_chat():
    print("Welcome to your AI Chatbot! Type 'exit', 'clear', 'restart', or 'history'.\n")

    
    role = input("Choose assistant's specialty (leave blank for default): ").strip()
    system_prompt = f"You are a helpful assistant specialized in {role}." if role else "You are a helpful assistant."

    
    session_id = input("Enter session ID (or leave blank to create new): ").strip()
    session_id = clean_session_id(session_id) or str(uuid.uuid4())

    
    session = CosmosSessionManager(session_id)
    conversation = [{"role": "system", "content": system_prompt}]
    if session.messages:
        conversation += session.messages

    print(f"Assistant Session started. ID: {session_id}")

  
    client, deployment_name = init_openai_client()

    while True:
        try:
            user_input = input("You: ").strip()

           
            if user_input.lower() in ["exit", "quit"]:
                print("Assistant: Goodbye!")
                break

           
            if user_input.lower() == "clear":
                session.clear()
                conversation = [{"role": "system", "content": system_prompt}]
                print("Assistant: Session cleared.\n")
                continue

            
            if user_input.lower() == "restart":
                session_id = str(uuid.uuid4())
                session = CosmosSessionManager(session_id)
                conversation = [{"role": "system", "content": system_prompt}]
                print(f"Assistant: New session started (ID: {session_id}).\n")
                continue

            if user_input.lower() == "history":
                if session.messages:
                    print("Assistant: Previous messages:\n")
                    for msg in session.messages:
                        if msg["role"] != "system":
                            print(f"{msg['role']}: {msg['content']}")
                    print()
                else:
                    print("Assistant: No messages yet.\n")
                continue

            # -------- RAG grounding (BM25) instead of raw user msg --------
            passages = search_top_k(user_input, k=5)
            sources_formatted = format_sources_for_prompt(passages)
            grounded_user_msg = make_grounded_user_message(user_input, sources_formatted)
            conversation.append(grounded_user_msg)
            # ---------------------------------------------------------------

            # Summarize if needed
            conversation = summarize(
                conversation=conversation,
                client=client,
                model=deployment_name
            )

           
            conversation = trim_conversation_by_tokens(
                conversation=conversation,
                max_tokens=8192,
                model=deployment_name,
                safety_margin=500
            )

            
            response = client.chat.completions.create(
                messages=conversation,
                max_tokens=4096,
                temperature=0.3,
                top_p=1.0,
                model=deployment_name,
            )

            assistant_reply = response.choices[0].message.content.strip()
            print(f"Assistant: {assistant_reply}")
            print("-" * 40 + "\n")

            conversation.append({"role": "assistant", "content": assistant_reply})

            
            session.messages = conversation[1:]
            session.save()

        except Exception as e:
            print(f"Error: {e}\n")
