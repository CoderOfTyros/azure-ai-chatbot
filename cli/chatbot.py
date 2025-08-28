from .openai_client import init_openai_client
from ..session.cosmos_session_manager import CosmosSessionManager
import uuid
import re

def clean_session_id(text):
    return re.sub(r"[^\w\-]", "", text.strip())

def start_chat():
    print("Welcome to your AI Chatbot! Type 'exit', 'clear', 'restart', or 'history'.\n")

    # Optional bot role
    role = input("Choose assistant's specialty (leave blank for default): ").strip()
    system_prompt = f"You are a helpful assistant specialized in {role}." if role else "You are a helpful assistant."

    # Get session ID from user
    session_id = input("Enter session ID (or leave blank to create new): ").strip()
    session_id = clean_session_id(session_id) or str(uuid.uuid4())

    # Create Cosmos session
    session = CosmosSessionManager(session_id)
    conversation = [{"role": "system", "content": system_prompt}]
    if session.messages:
        conversation += session.messages

    print(f"Assistant Session started. ID: {session_id}")

    # OpenAI client
    client, deployment_name = init_openai_client()

    while True:
        try:
            user_input = input("You: ").strip()

            # Exit
            if user_input.lower() in ["exit", "quit"]:
                print("Assistant: Goodbye!")
                break

            # Clear current session (keeps session_id)
            if user_input.lower() == "clear":
                session.clear()
                conversation = [{"role": "system", "content": system_prompt}]
                print("Assistant: Session cleared.\n")
                continue

            # Restart session (new session_id)
            if user_input.lower() == "restart":
                session_id = str(uuid.uuid4())
                session = CosmosSessionManager(session_id)
                conversation = [{"role": "system", "content": system_prompt}]
                print(f"Assistant: New session started (ID: {session_id}).\n")
                continue

            # Show chat history
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

            # Add user message
            conversation.append({"role": "user", "content": user_input})

            # Generate assistant reply
            response = client.chat.completions.create(
                messages=conversation,
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
                model=deployment_name,
            )

            assistant_reply = response.choices[0].message.content.strip()
            print(f"Assistant: {assistant_reply}")
            print("-" * 40 + "\n")

            conversation.append({"role": "assistant", "content": assistant_reply})

            # Save conversation to Cosmos
            session.messages = [m for m in conversation if m["role"] != "system"]
            session.save()

        except Exception as e:
            print(f"Error: {e}\n")
