import os
import io
import wave
import numpy as np
from faster_whisper import WhisperModel
from voice.audio import mulaw_to_pcm

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")

_model_cache = None


def get_model() -> WhisperModel:
    global _model_cache
    if _model_cache is None:
        print(f"Loading Whisper model: {WHISPER_MODEL_SIZE}")
        _model_cache = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        print("Whisper model loaded")
    return _model_cache


def transcribe_mulaw(mulaw_audio: bytes) -> str:
    if not mulaw_audio or len(mulaw_audio) < 100:
        return ""

    pcm_data = mulaw_to_pcm(mulaw_audio)
    audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
    audio_array = audio_array / 32768.0

    if len(audio_array) < 1600:
        return ""

    model = get_model()
    segments, info = model.transcribe(
        audio_array,
        language=WHISPER_LANGUAGE,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    transcript = " ".join(segment.text for segment in segments).strip()
    return transcript


if __name__ == "__main__":
    print("STT module loaded successfully")
    print(f"Model: {WHISPER_MODEL_SIZE}")
    print(f"Device: {WHISPER_DEVICE}")
    print(f"Language: {WHISPER_LANGUAGE}")
    model = get_model()
    print("Whisper ready")