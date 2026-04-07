import os
import time
import mlflow
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_EN = os.getenv("MLFLOW_EXPERIMENT_EN", "contractor-voice-bot-en")


def init_mlflow() -> None:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_EN)
    print(f"MLflow initialized: {MLFLOW_TRACKING_URI}")
    print(f"Experiment: {MLFLOW_EXPERIMENT_EN}")


def log_conversation(
    utterance: str,
    intent: str,
    agent_used: str,
    response: str,
    latency_seconds: float,
    success: bool = True,
) -> None:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_EN)

        with mlflow.start_run(run_name=f"{agent_used}_{int(time.time())}"):
            mlflow.log_param("utterance", utterance[:200])
            mlflow.log_param("intent", intent)
            mlflow.log_param("agent_used", agent_used)
            mlflow.log_param("model", os.getenv("OLLAMA_MODEL_EN", "unknown"))
            mlflow.log_param("llm_backend", os.getenv("LLM_BACKEND", "ollama"))

            mlflow.log_metric("latency_seconds", latency_seconds)
            mlflow.log_metric("success", 1.0 if success else 0.0)
            mlflow.log_metric("response_length", len(response))

            mlflow.log_text(response[:500], "response.txt")

    except Exception as e:
        import traceback
        print(f"MLflow logging failed: {e}")
        traceback.print_exc()

def log_rag_eval(
    question: str,
    rouge_score: float,
    chunks_retrieved: int,
) -> None:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_EN)

        with mlflow.start_run(run_name=f"rag_eval_{int(time.time())}"):
            mlflow.log_param("question", question[:200])
            mlflow.log_param("embed_model", "BAAI/bge-small-en-v1.5")
            mlflow.log_param("chunk_size", 256)

            mlflow.log_metric("rouge_score", rouge_score)
            mlflow.log_metric("chunks_retrieved", chunks_retrieved)

    except Exception as e:
        print(f"MLflow RAG eval logging failed: {e}")


if __name__ == "__main__":
    print("Testing MLflow tracker...")
    init_mlflow()

    print("Logging test conversation...")
    log_conversation(
        utterance="What are your business hours?",
        intent="faq",
        agent_used="faq",
        response="Our business hours are Monday through Friday 7AM to 6PM.",
        latency_seconds=2.3,
        success=True,
    )
    print("Done. Check http://localhost:5000 to see the run.")