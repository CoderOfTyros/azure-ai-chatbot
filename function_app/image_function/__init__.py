import azure.functions as func
import json
import logging

from .. import chatbot_function   # reuse your chatbot (for knowledge-base prompts)
from .image_utils import generate_image, sanitize_prompt


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        prompt = body.get("prompt")
        if not prompt:
            return func.HttpResponse(
                json.dumps({"error": "Missing prompt"}),
                status_code=400,
                mimetype="application/json"
            )

        # 1. Ask chatbot to expand into a visual description
        chatbot_req = func.HttpRequest(
            method="POST",
            url="/api/chatbot_function",
            body=json.dumps({
                "message": f"Describe this in visual detail for image generation: {prompt}"
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        chatbot_resp = chatbot_function.main(chatbot_req)
        chatbot_data = json.loads(chatbot_resp.get_body().decode())
        visual_prompt = chatbot_data.get("reply", prompt)
        visual_prompt = sanitize_prompt(visual_prompt)

        logging.info(f"Image prompt expanded to: {visual_prompt}")

        # 2. Generate image from Azure DALL·E
        image_result = generate_image(visual_prompt, size="1024x1024")

        return func.HttpResponse(
            json.dumps({
                "image": image_result,
                "used_prompt": visual_prompt
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Image generation error:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
