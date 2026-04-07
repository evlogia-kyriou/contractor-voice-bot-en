import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

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


def build_receptionist_agent() -> Agent:
    return Agent(
        role="Receptionist",
        goal=(
            "Greet the caller warmly and identify their intent. "
            "Classify the caller's request into exactly one of these "
            "categories: 'faq', 'booking', or 'escalate'. "
            "Return only the category word, nothing else."
        ),
        backstory=(
            "Your name is Sarah. You work the front desk at ABC Plumbing "
            "and HVAC Services in Austin, Texas. You have worked there for "
            "two years. You are warm, professional, and efficient. "
            "You speak naturally, not like a script. "
            "You never use bullet points or lists when speaking. "
            "You never say 'Certainly', 'Absolutely', or 'Of course'. "
            "You keep responses to two sentences maximum on a phone call."
        ),
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def classify_intent(caller_utterance: str) -> str:
    agent = build_receptionist_agent()

    task = Task(
        description=(
            f"A caller just said: '{caller_utterance}'\n\n"
            "Classify their intent into exactly one word:\n"
            "- 'faq' if they are asking a question about services, "
            "pricing, hours, warranty, payment, or service area\n"
            "- 'booking' if they want to schedule, book, or make "
            "an appointment\n"
            "- 'escalate' if the request is unclear, urgent, or outside "
            "the scope of FAQ and booking\n\n"
            "Return only the single word: faq, booking, or escalate. "
            "No punctuation, no explanation."
        ),
        expected_output="A single word: faq, booking, or escalate",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    intent = str(result).strip().lower()

    if intent not in ["faq", "booking", "escalate"]:
        intent = "escalate"

    return intent


def greet() -> str:
    agent = build_receptionist_agent()

    task = Task(
        description=(
            "A caller just called ABC Plumbing and HVAC Services. "
            "Greet them warmly and ask how you can help. "
            "Keep it to one or two natural sentences. "
            "Do not use bullet points or lists."
        ),
        expected_output="A warm one or two sentence greeting",
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
    print("Testing Receptionist agent...\n")

    print("1. Greeting test:")
    greeting = greet()
    print(f"   {greeting}\n")

    test_utterances = [
        "What are your business hours?",
        "I'd like to book an appointment for next Tuesday",
        "My pipe just burst and water is everywhere",
        "How much do you charge for HVAC repair?",
        "Can you fit me in tomorrow morning?",
        "I need to reschedule my appointment",
        "Do you work on weekends?",
        "asdfghjkl",
    ]

    print("2. Intent classification tests:")
    for utterance in test_utterances:
        intent = classify_intent(utterance)
        print(f"   '{utterance}'")
        print(f"   → {intent}\n")