import os
from pathlib import Path
from piper import PiperVoice
from voice.audio import text_to_mulaw

PIPER_VOICE_DIR = Path(os.path.expanduser("~/.local/share/piper"))
VOICE_MODEL = os.getenv("PIPER_VOICE_MODEL", "en_US-lessac-medium")

_voice_cache = None


def get_voice() -> PiperVoice:
    global _voice_cache
    if _voice_cache is None:
        model_path = PIPER_VOICE_DIR / f"{VOICE_MODEL}.onnx"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Voice model not found at {model_path}. "
                f"Download it first."
            )
        _voice_cache = PiperVoice.load(str(model_path))
        print(f"TTS voice loaded: {VOICE_MODEL}")
    return _voice_cache


def synthesize(text: str) -> bytes:
    voice = get_voice()
    mulaw_audio = text_to_mulaw(text, voice)
    return mulaw_audio


if __name__ == "__main__":
    print("Testing TTS...")
    test_phrases = [
        "Hi there, welcome to ABC Plumbing and HVAC Services.",
        "Our business hours are Monday through Friday, 7 AM to 6 PM.",
        "Your appointment has been booked for next Tuesday morning.",
    ]
    for phrase in test_phrases:
        audio = synthesize(phrase)
        print(f"Phrase: '{phrase[:50]}...'")
        print(f"Audio bytes: {len(audio)}")
        print()