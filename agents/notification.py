import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
CONTRACTOR_PHONE = os.getenv("CONTRACTOR_PHONE", "")
CONTRACTOR_NAME = os.getenv("CONTRACTOR_NAME", "ABC Plumbing and HVAC Services")


def send_sms(to: str, body: str) -> bool:
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print(f"[SMS MOCK] To: {to}")
        print(f"[SMS MOCK] Body: {body}")
        return True

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to,
        )
        print(f"SMS sent to {to}: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS failed to {to}: {e}")
        return False


def notify_booking(booking_details: dict, customer_phone: str = "") -> dict:
    date = booking_details.get("date", "TBD")
    time = booking_details.get("time", "TBD")
    service = booking_details.get("service", "service")
    name = booking_details.get("name", "Customer")

    contractor_msg = (
        f"New booking at {CONTRACTOR_NAME}:\n"
        f"Customer: {name}\n"
        f"Service: {service}\n"
        f"Date: {date}\n"
        f"Time: {time}\n"
        f"Phone: {customer_phone or 'not provided'}"
    )

    customer_msg = (
        f"Hi {name}, your appointment with {CONTRACTOR_NAME} "
        f"is confirmed for {date}"
        + (f" at {time}" if time != "TBD" else "")
        + f". We will call you to confirm the exact time window. "
        f"Questions? Call us at {TWILIO_PHONE_NUMBER}."
    )

    contractor_sent = send_sms(CONTRACTOR_PHONE, contractor_msg)
    customer_sent = False
    if customer_phone:
        customer_sent = send_sms(customer_phone, customer_msg)

    return {
        "contractor_notified": contractor_sent,
        "customer_notified": customer_sent,
        "contractor_message": contractor_msg,
        "customer_message": customer_msg,
    }


if __name__ == "__main__":
    print("Testing Notification agent (mock mode, no real Twilio keys yet)...\n")

    test_booking = {
        "date": "Tuesday April 15",
        "time": "10:00 AM",
        "service": "plumbing repair",
        "name": "John Smith",
        "phone": "not provided",
    }

    result = notify_booking(test_booking, customer_phone="")
    print(f"\nContractor notified: {result['contractor_notified']}")
    print(f"Customer notified: {result['customer_notified']}")