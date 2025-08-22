# function_app/chatbot_func/__init__.py
import azure.functions as func
import json


import sys
import os
sys.path.append(os.path.dirname(__file__))

from openai_client import init_openai_client

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        message = body.get("message")

        if not message:
            return func.HttpResponse("Missing 'message' field in JSON body", status_code=400)

        client, deployment_name = init_openai_client()

        conversation = [
            { "role": "system", "content": "You are a helpful assistant." },
            { "role": "user", "content": message }
        ]

        response = client.chat.completions.create(
            messages=conversation,
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            model=deployment_name
        )


        reply = response.choices[0].message.content

        return func.HttpResponse(
            json.dumps({ "reply": reply }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
