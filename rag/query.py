import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from rag.ingest import load_index

load_dotenv()

SIMILARITY_THRESHOLD = 0.3
TOP_K = 3
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_EN = os.getenv("OLLAMA_MODEL_EN", "llama3.1:8b-instruct-q4_K_M")


def build_query_engine(index: VectorStoreIndex) -> RetrieverQueryEngine:
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )
    Settings.llm = Ollama(
        model=OLLAMA_MODEL_EN,
        base_url=OLLAMA_BASE_URL,
        request_timeout=120.0,
    )

    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=TOP_K,
    )

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=SIMILARITY_THRESHOLD)
        ],
    )
    return query_engine


def query(question: str) -> str:
    index = load_index()
    engine = build_query_engine(index)
    response = engine.query(question)
    return str(response)


if __name__ == "__main__":
    test_questions = [
        "What services do you offer?",
        "What are your business hours?",
        "How much does a service call cost?",
        "Do you offer emergency services?",
        "What areas do you serve?",
    ]

    print("Testing RAG query engine with Ollama...\n")
    for q in test_questions:
        print(f"Q: {q}")
        answer = query(q)
        print(f"A: {answer}\n")