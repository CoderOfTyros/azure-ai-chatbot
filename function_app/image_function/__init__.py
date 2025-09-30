import azure.functions as func
import json
import logging
import uuid

from .. import chatbot_function   
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

        # get visual description
        chatbot_req = func.HttpRequest(
            method="POST",
            url="/api/chatbot_function",
            body=json.dumps({
                "message": f"Describe this in visual detail for image generation: {prompt}",
                "session_id": session_id,  
                "skip_session_save": True,
                "allow_image_tool": False  
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        chatbot_resp = chatbot_function.main(chatbot_req)
        chatbot_data = json.loads(chatbot_resp.get_body().decode())
        chatbot_reply = chatbot_data.get("reply", "")
        
        
        if "I can only generate images related to the stories in the knowledge base" in chatbot_reply:
           
            try:
                session = CosmosSessionManager(session_id)
                session.add_message("user", prompt)
                session.add_message("assistant", chatbot_reply)
                logging.info(f"Successfully saved image restriction response to session {session_id}")
            except Exception as db_error:
                logging.warning(f"Failed to save to Cosmos DB: {str(db_error)}")
            
            # Return the chatbot's response instead of generating an image
            return func.HttpResponse(
                json.dumps({
                    "error": chatbot_reply,
                    "session_id": session_id
                }),
                status_code=200,  
                mimetype="application/json"
            )
        
      
        visual_prompt = sanitize_prompt(chatbot_reply)
        logging.info(f"Image prompt expanded to: {visual_prompt}")


        image_result = generate_image(visual_prompt, size="1024x1024")

     
        try:
            session = CosmosSessionManager(session_id)
            
            session.add_message("user", prompt)
            session.add_message("assistant", image_result)
            
            logging.info(f"Successfully saved image generation to session {session_id}")
        except Exception as db_error:
            logging.warning(f"Failed to save to Cosmos DB: {str(db_error)}")
          

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
