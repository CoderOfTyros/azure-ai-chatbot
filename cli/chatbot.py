from openai_client import init_openai_client
import uuid
from cosmos_session_manager import CosmosSessionManager


def start_chat():
    session_id = input("Enter session ID (or leave blank to create one): ") or str(uuid.uuid4())
    session = CosmosSessionManager(session_id)
    print("Welcome to your AI Chatbot! Write 'exit' or 'quit' to quit.\n")


    client, deployment_name = init_openai_client()
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]


    while True:

        try: 

            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            session.add_message("user", user_input)
            conversation.append({"role": "user", "content": user_input})

            response = client.chat.completions.create(
                messages=conversation,
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
                model=deployment_name,
            )

             
            chatbot_output = response.choices[0].message.content
            print(f"Assistant: {chatbot_output}\n")

            session.add_message("assistant", chatbot_output)
            conversation.append({"role": "assistant", "content": chatbot_output})

        except Exception as e:
            print(f"Error: {e}\n")


