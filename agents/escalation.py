import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_EN = os.getenv("OLLAMA_MODEL_EN", "llama3.1:8b-instruct-q4_K_M")
CONTRACTOR_PHONE = os.getenv("CONTRACTOR_PHONE", "(512) 555-0147")


def get_llm() -> LLM:
    return LLM(
        model=f"ollama/{OLLAMA_MODEL_EN}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        temperature=0.3,
        timeout=120,
    )


def build_escalation_agent() -> Agent:
    return Agent(
        role="Escalation Handler",
        goal=(
            "Handle calls that are outside the scope of FAQ and booking. "
            "Acknowledge the caller's situation empathetically and provide "
            "a clear next step, either a callback from the team or an "
            "emergency contact number."
        ),
        backstory=(
            "Your name is Sarah. You work the front desk at ABC Plumbing "
            "and HVAC Services. When a situation is beyond what you can "
            "handle directly, you make sure the caller feels heard and "
            "knows exactly what happens next. You are calm, empathetic, "
            "and clear. You speak in short natural sentences. "
            "You never use bullet points or lists."
        ),
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def handle_escalation(caller_utterance: str, reason: str = "unclear") -> str:
    agent = build_escalation_agent()

    task = Task(
        description=(
            f"A caller said: '{caller_utterance}'\n"
            f"Escalation reason: {reason}\n\n"
            "Respond to the caller empathetically in one or two natural "
            "sentences suitable for a phone call. "
            "Acknowledge their situation and let them know that a team "
            f"member will call them back, or they can call directly at "
            f"{CONTRACTOR_PHONE} for urgent matters. "
            "Do not use bullet points or lists. "
            "Do not make promises about timing you cannot keep."
        ),
        expected_output=(
            "A natural empathetic one or two sentence escalation response"
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    return str(crew.kickoff()).strip()


if __name__ == "__main__":
    test_cases = [
        {
            "utterance": "My pipe just burst and water is flooding my basement",
            "reason": "emergency situation requiring immediate human response",
        },
        {
            "utterance": "I want to complain about the work your technician did last week",
            "reason": "complaint requiring human handling",
        },
        {
            "utterance": "asdfghjkl",
            "reason": "unclear or garbled input",
        },
        {
            "utterance": "I need to speak to a manager",
            "reason": "caller requesting human escalation",
        },
    ]

    print("Testing Escalation agent...\n")
    for case in test_cases:
        print(f"Caller: '{case['utterance']}'")
        print(f"Reason: {case['reason']}")
        response = handle_escalation(case["utterance"], case["reason"])
        print(f"Response: {response}\n")