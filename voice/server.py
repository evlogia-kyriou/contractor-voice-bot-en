import os
import json
import base64
import asyncio
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response, FileResponse
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from prometheus_fastapi_instrumentator import Instrumentator
from voice.stt import transcribe_mulaw
from voice.tts import synthesize
from agents.pipeline import run_conversation, greet

app = FastAPI(title="Contractor Voice Bot EN")
Instrumentator().instrument(app).expose(app)

AUDIO_BUFFER_SECONDS = 3
SAMPLE_RATE = 8000
BUFFER_SIZE = SAMPLE_RATE * AUDIO_BUFFER_SECONDS


@app.get("/health")
async def health():
    return {"status": "ok", "service": "contractor-voice-bot-en"}

@app.post("/test-pipeline")
async def test_pipeline(request: Request):
    from observability.phoenix_tracer import init_tracer
    from observability.mlflow_tracker import init_mlflow
    from agents.pipeline import run_demo
    init_tracer()
    init_mlflow()
    run_demo()
    return {"status": "done", "message": "Pipeline test complete. Check Grafana."}

@app.get("/token")
async def get_token():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    api_key = os.getenv("TWILIO_API_KEY")
    api_secret = os.getenv("TWILIO_API_SECRET")
    twiml_app_sid = os.getenv("TWILIO_TWIML_APP_SID")

    token = AccessToken(
        account_sid,
        api_key,
        api_secret,
        identity="browser-client"
    )

    voice_grant = VoiceGrant(
        outgoing_application_sid=twiml_app_sid,
        incoming_allow=True,
    )
    token.add_grant(voice_grant)
    return {"token": token.to_jwt()}


@app.get("/client")
async def client():
    return FileResponse("voice/client.html")

@app.post("/incoming-call")
async def incoming_call(request: Request):
    host = request.headers.get("host", "localhost")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Call connected")

    audio_buffer = bytearray()
    stream_sid = None
    call_active = True
    silence_counter = 0
    MAX_SILENCE = 8

    try:
        greeting_sent = False

        while call_active:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                data = json.loads(message)
                event = data.get("event")

                if event == "start":
                    stream_sid = data["start"]["streamSid"]
                    print(f"Stream started: {stream_sid}")
                    await asyncio.sleep(1.0)
                    greeting_text = greet()
                    greeting_audio = synthesize(greeting_text)
                    if greeting_audio:
                        await send_audio(websocket, greeting_audio, stream_sid)
                        print(f"Greeting sent: {greeting_text}")
                    greeting_sent = True

                elif event == "media":
                    payload = data["media"]["payload"]
                    audio_chunk = base64.b64decode(payload)
                    audio_buffer.extend(audio_chunk)

                    if len(audio_buffer) >= BUFFER_SIZE:
                        audio_data = bytes(audio_buffer)
                        audio_buffer.clear()

                        transcript = transcribe_mulaw(audio_data)
                        print(f"Transcribed: '{transcript}'")

                        if transcript and len(transcript.strip()) > 2:
                            silence_counter = 0
                            result = run_conversation(transcript)
                            response_text = result.get("response", "")

                            if response_text:
                                response_audio = synthesize(response_text)
                                if response_audio:
                                    await send_audio(
                                        websocket,
                                        response_audio,
                                        stream_sid
                                    )
                                    print(f"Response sent: {response_text[:80]}")
                        else:
                            silence_counter += 1
                            if silence_counter >= MAX_SILENCE:
                                prompt = "I'm still here. How can I help you?"
                                audio = synthesize(prompt)
                                if audio:
                                    await send_audio(websocket, audio, stream_sid)
                                silence_counter = 0

                elif event == "stop":
                    print("Call ended by Twilio")
                    call_active = False

            except asyncio.TimeoutError:
                print("Connection timeout")
                call_active = False

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error in media stream: {e}")
    finally:
        print("Call session ended")


async def send_audio(websocket: WebSocket, audio: bytes, stream_sid: str):
    if not audio or not stream_sid:
        return
    chunk_size = 160
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i + chunk_size]
        payload = base64.b64encode(chunk).decode("utf-8")
        message = json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": payload
            }
        })
        try:
            await websocket.send_text(message)
        except Exception:
            break


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)