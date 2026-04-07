import os
import json
import base64
import asyncio
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response, FileResponse
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from prometheus_fastapi_instrumentator import Instrumentator
from voice.stt import transcribe_mulaw
from voice.tts import synthesize
from agents.pipeline import run_conversation, greet
import time

from observability.phoenix_tracer import init_tracer
init_tracer()

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

    tracer = trace.get_tracer("voice-bot")
    audio_buffer = bytearray()
    stream_sid = None
    call_active = True
    silence_counter = 0
    MAX_SILENCE = 8
    is_speaking = False

    with tracer.start_as_current_span("call_session") as call_span:
        call_span.set_attribute("service", "contractor-voice-bot-en")
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

                            with tracer.start_as_current_span("stt") as stt_span:
                                stt_start = time.time()
                                transcript = transcribe_mulaw(audio_data)
                                stt_span.set_attribute("latency_ms", int((time.time() - stt_start) * 1000))
                                stt_span.set_attribute("transcript", transcript)
                            print(f"Transcribed: '{transcript}'")

                            if transcript and len(transcript.strip()) > 2 and not is_speaking:
                                silence_counter = 0
                                with tracer.start_as_current_span("conversation_turn") as turn_span:
                                    turn_span.set_attribute("transcript", transcript)
                                    result = run_conversation(transcript)
                                    turn_span.set_attribute("intent", result.get("intent", ""))
                                    turn_span.set_attribute("agent", result.get("agent_used", ""))
                                    turn_span.set_attribute("response", result.get("response", "")[:200])
                                response_text = result.get("response", "")

                                if response_text:
                                    is_speaking = True
                                    with tracer.start_as_current_span("tts") as tts_span:
                                        tts_start = time.time()
                                        response_audio = synthesize(response_text)
                                        tts_span.set_attribute("latency_ms", int((time.time() - tts_start) * 1000))
                                        tts_span.set_attribute("text_length", len(response_text))
                                    if response_audio:
                                        await send_audio(
                                            websocket,
                                            response_audio,
                                            stream_sid
                                        )
                                        print(f"Response sent: {response_text[:80]}")
                                    await asyncio.sleep(len(response_text) * 0.06)
                                    is_speaking = False
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
            call_span.set_status(Status(StatusCode.ERROR, str(e)))
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