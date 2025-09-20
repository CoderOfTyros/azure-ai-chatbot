import azure.functions as func
import logging
import json
import base64

from .speech_utils import speech_to_text, text_to_speech, normalize_audio_bytes
from .. import chatbot_function


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # --- Case 1: TTS only (frontend sends JSON {"text": "..."}) ---
        try:
            body = req.get_json()
        except Exception:
            body = None

        if body and "text" in body:
            reply_text = body["text"]
            audio_reply = text_to_speech(reply_text)
            audio_b64 = base64.b64encode(audio_reply).decode("utf-8")

            return func.HttpResponse(
                json.dumps({"tts": audio_b64}),
                status_code=200,
                mimetype="application/json"
            )

        # --- Case 2: STT + chatbot (no TTS here) ---
        audio_file = req.files.get("file") if hasattr(req, "files") else None
        if not audio_file:
            return func.HttpResponse("Missing audio file or text field.", status_code=400)

        audio_bytes = audio_file.read()
        audio_bytes = normalize_audio_bytes(audio_bytes)

        # --- Session ID handling ---
        session_id = req.params.get("session_id")
        if not session_id and hasattr(req, "form") and req.form is not None:
            session_id = req.form.get("session_id")
        logging.info(f"Session ID: {session_id}")

        # --- STT ---
        user_input = speech_to_text(audio_bytes)
        logging.info(f"STT result: {user_input}")

        # --- Call chatbot_function ---
        body = {"message": user_input, "session_id": session_id}
        chatbot_req = func.HttpRequest(
            method="POST",
            url="/api/chatbot_function",
            body=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        chatbot_resp = chatbot_function.main(chatbot_req)
        chatbot_data = json.loads(chatbot_resp.get_body().decode())

        reply_text = chatbot_data.get("reply", "")

        # --- Response (text only, no TTS) ---
        return func.HttpResponse(
            json.dumps({
                "stt": user_input,
                "reply": reply_text,
                "session_id": chatbot_data.get("session_id")
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Speech function error:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
