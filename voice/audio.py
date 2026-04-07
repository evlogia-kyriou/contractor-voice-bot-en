import audioop
import wave
import io


def pcm_to_mulaw(pcm_data: bytes, sample_rate: int = 22050) -> bytes:
    if sample_rate != 8000:
        pcm_data, _ = audioop.ratecv(
            pcm_data, 2, 1, sample_rate, 8000, None
        )
    mulaw_data = audioop.lin2ulaw(pcm_data, 2)
    return mulaw_data


def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
    pcm_data, _ = audioop.ratecv(pcm_data, 2, 1, 8000, 16000, None)
    return pcm_data


def wav_to_mulaw(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_file:
        sample_rate = wav_file.getframerate()
        pcm_data = wav_file.readframes(wav_file.getnframes())
    return pcm_to_mulaw(pcm_data, sample_rate)


def text_to_mulaw(text: str, voice) -> bytes:
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, 'wb') as wav_file:
        voice.synthesize_wav(text, wav_file, set_wav_format=True)
    audio_buffer.seek(0)
    wav_bytes = audio_buffer.read()
    if len(wav_bytes) <= 44:
        return b""
    return wav_to_mulaw(wav_bytes)