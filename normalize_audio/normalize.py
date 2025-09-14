from pydub import AudioSegment

def normalize_audio_file(input_path: str, output_path: str) -> None:
    """
    Normalize any audio file (WAV/MP3/M4A/etc) to PCM WAV, 16kHz mono, 16-bit.
    Saves the result as a new .wav file for Azure STT.
    """
    # Load audio file with pydub
    audio = AudioSegment.from_file(input_path)

    # Convert → mono, 16kHz, 16-bit PCM
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    # Export as proper WAV file
    audio.export(output_path, format="wav", codec="pcm_s16le")
    print(f"✅ Normalized audio saved to {output_path}")


# Example usage:
if __name__ == "__main__":
    normalize_audio_file("example.m4a", "normalized.wav")
