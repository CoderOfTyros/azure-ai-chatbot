import os, io
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment

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
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "[Unrecognized speech]"
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




def normalize_audio_bytes(data: bytes) -> bytes:
    """
    Normalize raw audio bytes (any format) → PCM WAV, 16kHz mono, 16-bit.
    Returns new WAV bytes.
    """
    # Load from bytes
    audio = AudioSegment.from_file(io.BytesIO(data))

    # Normalize
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    # Export back to bytes
    out_io = io.BytesIO()
    audio.export(out_io, format="wav", codec="pcm_s16le")
    return out_io.getvalue()
