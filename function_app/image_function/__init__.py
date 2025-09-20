import azure.functions as func
import json
import logging
import uuid

from .. import chatbot_function   # reuse your chatbot (for knowledge-base prompts)
from .image_utils import generate_image, sanitize_prompt
from ..chatbot_function.cosmos_session_manager import CosmosSessionManager


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        prompt = body.get("prompt")
        session_id = body.get("session_id") or str(uuid.uuid4())
        
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

        # 3. Save user prompt and image URL to Cosmos DB
        try:
            session = CosmosSessionManager(session_id)
            
            # Add user message with original prompt
            session.add_message("user", f"Generate an image: {prompt}")
            
            # Add assistant message with image URL and expanded prompt
            session.add_message("assistant", f"I've generated an image for you. Here's the image URL: {image_result}\n\nExpanded prompt used: {visual_prompt}")
            
            logging.info(f"Successfully saved image generation to session {session_id}")
        except Exception as db_error:
            logging.warning(f"Failed to save to Cosmos DB: {str(db_error)}")
            # Continue execution even if DB save fails

        return func.HttpResponse(
            json.dumps({
                "image": image_result,
                "used_prompt": visual_prompt,
                "session_id": session_id
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
