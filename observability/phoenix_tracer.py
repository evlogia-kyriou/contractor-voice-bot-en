import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://localhost")
PHOENIX_PORT = os.getenv("PHOENIX_PORT", "6006")


def init_tracer(project_name: str = "contractor-voice-bot-en") -> None:
    try:
        from phoenix.otel import register
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
        from openinference.instrumentation.crewai import CrewAIInstrumentor

        tracer_provider = register(
            project_name=project_name,
            endpoint=f"{PHOENIX_HOST}:{PHOENIX_PORT}/v1/traces",
        )
        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
        CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print(f"Phoenix tracer initialized: {PHOENIX_HOST}:{PHOENIX_PORT}")
        print(f"Project: {project_name}")
        return tracer_provider

    except Exception as e:
        print(f"Phoenix tracer failed to initialize: {e}")
        return None


if __name__ == "__main__":
    provider = init_tracer()
    if provider:
        print("Tracer is ready")
        print(f"View traces at: {PHOENIX_HOST}:{PHOENIX_PORT}")