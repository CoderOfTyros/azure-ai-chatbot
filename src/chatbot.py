from openai_client import init_openai_client


def start_chat():

    print("Welcome to your AI Chatbot! Write 'exit' to quit.\n")


    client, deployment_name = init_openai_client()
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]


    while True:

        try: 

            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

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

            conversation.append({"role": "assistant", "content": chatbot_output})

        except Exception as e:
            print(f"Error: {e}\n")


