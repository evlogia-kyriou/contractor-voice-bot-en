import os
from dotenv import load_dotenv, find_dotenv
from agents.receptionist import classify_intent, greet
from agents.faq import answer_question
from agents.booking import extract_booking_details, confirm_booking, book_with_calendar
from agents.escalation import handle_escalation
from agents.notification import notify_booking

load_dotenv(find_dotenv(), override=True)


def run_conversation(caller_utterance: str, customer_phone: str = "") -> dict:
    """
    Full conversation pipeline. Takes a caller utterance and runs it
    through the appropriate agents. Returns a dict with the response
    and metadata about what happened.
    """

    result = {
        "utterance": caller_utterance,
        "intent": None,
        "response": None,
        "booking_details": None,
        "notifications": None,
        "agent_used": None,
    }

    print(f"\n{'='*60}")
    print(f"Caller: '{caller_utterance}'")
    print(f"{'='*60}")

    # Step 1: Receptionist classifies intent
    print("→ Receptionist classifying intent...")
    intent = classify_intent(caller_utterance)
    result["intent"] = intent
    print(f"→ Intent: {intent}")

    # Step 2: Route to the correct agent
    if intent == "faq":
        print("→ Routing to FAQ agent...")
        response = answer_question(caller_utterance)

        # Post-routing check: if FAQ agent could not find relevant context
        # escalate instead of returning a confused response
        escalation_triggers = [
            "doesn't make sense",
            "don't make sense",
            "could you please rephrase",
            "i'm not sure",
            "i don't have that information",
            "cannot find",
            "not able to find",
            "please rephrase",
            "unclear",
            "didn't quite catch",
            "didn't catch",
            "repeat that",
            "come again",
        ]

        response_lower = response.lower()
        faq_failed = any(trigger in response_lower for trigger in escalation_triggers)

        if faq_failed:
            print("→ FAQ agent could not resolve. Escalating...")
            response = handle_escalation(
                caller_utterance,
                reason="FAQ agent could not find relevant context"
            )
            result["agent_used"] = "escalation"
            intent = "escalate"
            result["intent"] = intent
            print(f"→ Escalation response: {response}")
        else:
            result["agent_used"] = "faq"
            print(f"→ FAQ response: {response}")

        result["response"] = response

    elif intent == "booking":
        print("→ Routing to Booking agent...")
        booking_result = book_with_calendar(caller_utterance, customer_phone)
        result["booking_details"] = booking_result.get("details")
        result["agent_used"] = "booking"

        if booking_result["success"]:
            result["response"] = booking_result["confirmation"]
            print(f"→ Confirmation: {booking_result['confirmation']}")
            if booking_result.get("calendar_result"):
                print(f"→ Calendar link: {booking_result['calendar_result']['event_link']}")

            print("→ Routing to Notification agent...")
            notifications = notify_booking(
                booking_result.get("details", {}),
                customer_phone,
            )
            result["notifications"] = notifications
            print(f"→ Contractor notified: {notifications['contractor_notified']}")
            print(f"→ Customer notified: {notifications['customer_notified']}")
        else:
            result["response"] = booking_result["confirmation"]
            result["agent_used"] = "escalation"
            print(f"→ Booking failed, escalating: {booking_result['confirmation']}")

    else:
        print("→ Routing to Escalation agent...")
        response = handle_escalation(caller_utterance, reason="unclear or out of scope")
        result["response"] = response
        result["agent_used"] = "escalation"
        print(f"→ Escalation response: {response}")

    return result


def run_demo() -> None:
    """
    Runs the 10 demo scenarios that will be used for the client recording.
    """
    print("\n" + "="*60)
    print("CONTRACTOR VOICE BOT - EN REPO - FULL PIPELINE TEST")
    print("="*60)

    # Greet first
    print("\n→ Generating greeting...")
    greeting = greet()
    print(f"Bot: {greeting}")

    scenarios = [
        {
            "label": "Scenario 1: FAQ - business hours",
            "utterance": "What are your business hours?",
            "customer_phone": "",
        },
        {
            "label": "Scenario 2: FAQ - pricing",
            "utterance": "How much do you charge for a service call?",
            "customer_phone": "",
        },
        {
            "label": "Scenario 3: FAQ - service area",
            "utterance": "Do you serve the Round Rock area?",
            "customer_phone": "",
        },
        {
            "label": "Scenario 4: Booking - next Tuesday",
            "utterance": "I'd like to book a plumbing repair for next Tuesday morning",
            "customer_phone": "",
        },
        {
            "label": "Scenario 5: Booking - with name and phone",
            "utterance": "Book me in for Friday, my name is John and my number is 512-555-0199",
            "customer_phone": "512-555-0199",
        },
        {
            "label": "Scenario 6: Booking - slot unavailable fallback",
            "utterance": "Can you fit me in tomorrow at 9am?",
            "customer_phone": "",
        },
        {
            "label": "Scenario 7: Escalation - emergency",
            "utterance": "My pipe just burst and water is everywhere",
            "customer_phone": "",
        },
        {
            "label": "Scenario 8: Escalation - complaint",
            "utterance": "I want to complain about the work done last week",
            "customer_phone": "",
        },
        {
            "label": "Scenario 9: FAQ - warranty",
            "utterance": "Do you offer any warranty on your work?",
            "customer_phone": "",
        },
        {
            "label": "Scenario 10: Escalation - garbled input",
            "utterance": "asdfghjkl",
            "customer_phone": "",
        },
    ]

    passed = 0
    total = len(scenarios)

    for scenario in scenarios:
        print(f"\n{'-'*60}")
        print(f"[{scenario['label']}]")
        result = run_conversation(
            scenario["utterance"],
            scenario["customer_phone"],
        )

        expected_intents = {
            "Scenario 1": "faq",
            "Scenario 2": "faq",
            "Scenario 3": "faq",
            "Scenario 4": "booking",
            "Scenario 5": "booking",
            "Scenario 6": "booking",
            "Scenario 7": "escalate",
            "Scenario 8": "escalate",
            "Scenario 9": "faq",
            "Scenario 10": "escalate",
        }

        label_key = scenario["label"].split(":")[0]
        expected = expected_intents.get(label_key, "unknown")
        correct = result["intent"] == expected
        if correct:
            passed += 1

        print(f"Expected intent: {expected} | Got: {result['intent']} | {'PASS' if correct else 'FAIL'}")

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} scenarios routed correctly")
    print(f"Autonomous resolution rate: {passed/total*100:.0f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_demo()