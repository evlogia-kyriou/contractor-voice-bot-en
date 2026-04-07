import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from rag.ingest import load_index
from rag.query import build_query_engine

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_EN = os.getenv("OLLAMA_MODEL_EN", "llama3.1:8b-instruct-q4_K_M")


def get_llm() -> LLM:
    return LLM(
        model=f"ollama/{OLLAMA_MODEL_EN}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        temperature=0.3,
        timeout=120,
    )


def build_faq_agent() -> Agent:
    return Agent(
        role="FAQ Specialist",
        goal=(
            "Answer the caller's question accurately using only information "
            "from the contractor's documents. Keep answers short and natural "
            "for a phone conversation. Never make up information."
        ),
        backstory=(
            "Your name is Sarah. You work the front desk at ABC Plumbing "
            "and HVAC Services in Austin, Texas. You know the business "
            "inside and out: services, pricing, hours, warranty, and "
            "service area. You speak in short natural sentences. "
            "You never use bullet points or lists on a phone call. "
            "If you do not know something, you say so honestly and offer "
            "to have someone call them back."
        ),
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def answer_question(question: str) -> str:
    index = load_index()
    engine = build_query_engine(index)
    retrieved = engine.query(question)
    context = str(retrieved)

    agent = build_faq_agent()

    task = Task(
        description=(
            f"A caller asked: '{question}'\n\n"
            f"Here is the relevant information from our documents:\n"
            f"{context}\n\n"
            "Answer the caller's question in one or two natural sentences "
            "suitable for a phone conversation. "
            "Do not use bullet points or lists. "
            "Do not make up any information not present in the context. "
            "If the context does not contain the answer, say: "
            "'I don't have that information on hand, but I can have "
            "someone call you back with the details.'"
        ),
        expected_output=(
            "A natural one or two sentence answer suitable for a phone call"
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result).strip()


if __name__ == "__main__":
    test_questions = [
        "What are your business hours?",
        "How much does a service call cost?",
        "Do you offer emergency plumbing services?",
        "What areas do you serve?",
        "Do you work on weekends?",
        "What is your warranty policy?",
        "Do you accept credit cards?",
        "Can you fix a broken water heater?",
    ]

    print("Testing FAQ agent...\n")
    for q in test_questions:
        print(f"Q: {q}")
        answer = answer_question(q)
        print(f"A: {answer}\n")