import os
from integrations.calendar import get_available_slots, book_appointment as calendar_book
from datetime import datetime, timedelta
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_EN = os.getenv("OLLAMA_MODEL_EN", "llama3.1:8b-instruct-q4_K_M")
CONTRACTOR_NAME = os.getenv("CONTRACTOR_NAME", "ABC Plumbing and HVAC Services")


def get_llm() -> LLM:
    return LLM(
        model=f"ollama/{OLLAMA_MODEL_EN}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        temperature=0.2,
        timeout=120,
    )


def build_booking_agent() -> Agent:
    return Agent(
        role="Booking Coordinator",
        goal=(
            "Help the caller book an appointment. "
            "Extract the preferred date and time from the caller's message. "
            "Confirm the booking details clearly and naturally."
        ),
        backstory=(
            "Your name is Sarah. You coordinate appointments at ABC Plumbing "
            "and HVAC Services. You are efficient and precise with scheduling. "
            "You confirm appointment details clearly without repeating yourself. "
            "You speak in short natural sentences suitable for a phone call. "
            "You never use bullet points or lists."
        ),
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def extract_booking_details(caller_utterance: str) -> dict:
    agent = build_booking_agent()
    today = datetime.now().strftime("%A %d %B %Y")

    task = Task(
        description=(
            f"Today is {today}.\n"
            f"A caller said: '{caller_utterance}'\n\n"
            "Extract the booking details from their message and return "
            "them in this exact format with no extra text:\n"
            "date: <the date they want>\n"
            "time: <the time they want or 'not specified'>\n"
            "service: <the service they need or 'not specified'>\n"
            "name: <their name if mentioned or 'not provided'>\n"
            "phone: <their phone number if mentioned or 'not provided'>"
        ),
        expected_output=(
            "Booking details in the exact format specified: "
            "date, time, service, name, phone each on its own line"
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = str(crew.kickoff()).strip()

    details = {
        "date": "not specified",
        "time": "not specified",
        "service": "not specified",
        "name": "not provided",
        "phone": "not provided",
    }

    for line in result.split("\n"):
        for key in details:
            if line.lower().startswith(f"{key}:"):
                details[key] = line.split(":", 1)[1].strip()

    return details


def confirm_booking(details: dict) -> str:
    agent = build_booking_agent()

    task = Task(
        description=(
            f"You just booked an appointment with these details:\n"
            f"Date: {details['date']}\n"
            f"Time: {details['time']}\n"
            f"Service: {details['service']}\n"
            f"Customer name: {details['name']}\n\n"
            "Confirm the booking to the caller in one or two natural "
            "sentences suitable for a phone call. "
            "Mention that they will receive a confirmation message. "
            "Do not use bullet points or lists."
        ),
        expected_output=(
            "A natural one or two sentence booking confirmation"
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
    test_utterances = [
        "I'd like to book a plumbing repair for next Tuesday morning",
        "Can you fit me in tomorrow afternoon around 2pm?",
        "I need someone to look at my AC, maybe Thursday?",
        "Book me in for Friday, my name is John and my number is 512-555-0199",
    ]

    print("Testing Booking agent...\n")
    for utterance in test_utterances:
        print(f"Caller: '{utterance}'")
        details = extract_booking_details(utterance)
        print(f"Extracted details:")
        for k, v in details.items():
            print(f"  {k}: {v}")
        confirmation = confirm_booking(details)
        print(f"Confirmation: {confirmation}\n")

def book_with_calendar(
    caller_utterance: str,
    customer_phone: str = "",
) -> dict:
    details = extract_booking_details(caller_utterance)
    date = details.get("date", "not specified")
    time = details.get("time", "not specified")
    service = details.get("service", "general service")
    name = details.get("name", "Customer")

    if date == "not specified":
        return {
            "success": False,
            "details": details,
            "confirmation": "I did not catch the date you wanted. Could you tell me which day works best for you?",
        }

    available = get_available_slots(date)

    if not available:
        return {
            "success": False,
            "details": details,
            "confirmation": f"It looks like we are fully booked on {date}. Could you suggest another day?",
        }

    if time == "not specified" or time == "morning":
        chosen_time = available[0]
    elif time == "afternoon":
        afternoon_slots = [s for s in available if int(s.split(":")[0]) >= 12]
        chosen_time = afternoon_slots[0] if afternoon_slots else available[0]
    else:
        chosen_time = time

    result = calendar_book(
        summary=service,
        date_str=date,
        time_str=chosen_time,
        customer_name=name,
        customer_phone=customer_phone,
        duration_minutes=120,
    )

    if result["success"]:
        confirmation = confirm_booking({
            "date": result["start"],
            "time": chosen_time,
            "service": service,
            "name": name,
        })
        return {
            "success": True,
            "details": details,
            "calendar_result": result,
            "confirmation": confirmation,
        }
    else:
        return {
            "success": False,
            "details": details,
            "confirmation": "I had trouble booking that slot. Let me have someone from our team call you back to confirm.",
        }