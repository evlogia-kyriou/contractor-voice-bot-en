import os
from dotenv import load_dotenv

load_dotenv(override=True)


def send_sms(to: str, body: str) -> bool:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "")

    if not all([account_sid, auth_token]):
        print(f"[SMS MOCK] To: {to}")
        print(f"[SMS MOCK] Body: {body}")
        return True

    if "xxx" in account_sid.lower():
        print(f"[SMS MOCK - placeholder credentials] To: {to}")
        print(f"[SMS MOCK] Body: {body}")
        return True

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        params = {
            "body": body,
            "to": to,
        }

        if messaging_service_sid:
            params["messaging_service_sid"] = messaging_service_sid
        elif phone_number:
            params["from_"] = phone_number

        message = client.messages.create(**params)
        print(f"SMS sent to {to}: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS failed to {to}: {e}")
        return False


if __name__ == "__main__":
    print("Testing SMS integration...\n")

    to_number = os.getenv("CONTRACTOR_PHONE", "")
    if not to_number:
        print("Set CONTRACTOR_PHONE in .env to your verified Indonesian number")
    else:
        print(f"Sending test SMS to {to_number}...")
        result = send_sms(
            to_number,
            "Test message from Contractor Voice Bot. If you receive this, SMS is working!"
        )
        print(f"Result: {result}")