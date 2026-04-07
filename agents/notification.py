import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from integrations.sms import send_sms

CONTRACTOR_PHONE = os.getenv("CONTRACTOR_PHONE", "")
CONTRACTOR_NAME = os.getenv("CONTRACTOR_NAME", "ABC Plumbing and HVAC Services")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")


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
        + f". Questions? Call us at {TWILIO_PHONE_NUMBER}."
    )

    contractor_sent = False
    customer_sent = False

    if CONTRACTOR_PHONE:
        contractor_sent = send_sms(CONTRACTOR_PHONE, contractor_msg)
    else:
        print(f"[NOTIFICATION] Contractor message:\n{contractor_msg}")
        contractor_sent = True

    if customer_phone:
        customer_sent = send_sms(customer_phone, customer_msg)
    else:
        print(f"[NOTIFICATION] No customer phone provided, skipping SMS")

    return {
        "contractor_notified": contractor_sent,
        "customer_notified": customer_sent,
        "contractor_message": contractor_msg,
        "customer_message": customer_msg,
    }


if __name__ == "__main__":
    print("Testing Notification agent...\n")

    test_booking = {
        "date": "Tuesday 14 April 2026",
        "time": "10:00 AM",
        "service": "plumbing repair",
        "name": "John Smith",
    }

    result = notify_booking(test_booking, customer_phone="")
    print(f"\nContractor notified: {result['contractor_notified']}")
    print(f"Customer notified: {result['customer_notified']}")