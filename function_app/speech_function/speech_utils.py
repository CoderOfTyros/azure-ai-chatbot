import os, logging
import azure.cognitiveservices.speech as speechsdk

speech_key = os.environ.get("AZURE_SPEECH_KEY")
speech_region = os.environ.get("AZURE_SPEECH_REGION")

if not speech_key or not speech_region:
    raise RuntimeError("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in environment.")

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
speech_config.speech_recognition_language = "en-US"  


# ---------- Speech to Text ----------
def speech_to_text(audio_bytes: bytes) -> str:
    """Convert audio bytes (WAV/MP3) to text using Azure Speech."""
 
    push_stream = speechsdk.audio.PushAudioInputStream()
    push_stream.write(audio_bytes)
    push_stream.close()

    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
         logging.info(f"STT recognized: {result.text}")
         return result.text
    
    elif result.reason == speechsdk.ResultReason.NoMatch:
         logging.warning(f"STT NoMatch: {result.no_match_details}")
         return "[Unrecognized speech]"
    
    elif result.reason == speechsdk.ResultReason.Canceled:
         cancellation = result.cancellation_details
         logging.error(f"STT canceled: {cancellation.reason}, {cancellation.error_details}")
         return "[Recognition canceled]"
  
    else:
         raise RuntimeError(f"STT failed: {result.reason}")


# ---------- Text to Speech ----------
def text_to_speech(text: str) -> bytes:
    """Convert text to speech (WAV audio) and return raw bytes."""
   
    stream = speechsdk.audio.PullAudioOutputStream()
    audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data  # contains WAV bytes
    else:
        raise RuntimeError(f"TTS failed: {result.reason}")





