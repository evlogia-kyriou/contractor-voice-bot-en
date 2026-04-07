import os
import datetime
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")


def get_calendar_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=8080, open_browser=True)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service


def get_available_slots(
    date_str: str,
    duration_minutes: int = 120,
    business_start: int = 7,
    business_end: int = 18,
) -> list:
    try:
        service = get_calendar_service()

        try:
            date = datetime.datetime.strptime(date_str, "%d %B %Y")
        except ValueError:
            try:
                date = datetime.datetime.strptime(date_str, "%A %d %B %Y")
            except ValueError:
                date = datetime.datetime.now() + datetime.timedelta(days=1)

        day_start = date.replace(
            hour=business_start, minute=0, second=0, microsecond=0
        )
        day_end = date.replace(
            hour=business_end, minute=0, second=0, microsecond=0
        )

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=day_start.isoformat() + "Z",
            timeMax=day_end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        busy_times = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            busy_times.append((start, end))

        available_slots = []
        slot_start = day_start
        while slot_start + datetime.timedelta(minutes=duration_minutes) <= day_end:
            slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
            slot_free = True

            for busy_start, busy_end in busy_times:
                if "T" in busy_start:
                    busy_start_dt = datetime.datetime.fromisoformat(
                        busy_start.replace("Z", "")
                    ).replace(tzinfo=None)
                else:
                    busy_start_dt = datetime.datetime.strptime(busy_start, "%Y-%m-%d")

                if "T" in busy_end:
                    busy_end_dt = datetime.datetime.fromisoformat(
                        busy_end.replace("Z", "")
                    ).replace(tzinfo=None)
                else:
                    busy_end_dt = datetime.datetime.strptime(busy_end, "%Y-%m-%d")
                if not (slot_end <= busy_start_dt or slot_start >= busy_end_dt):
                    slot_free = False
                    break

            if slot_free:
                available_slots.append(
                    slot_start.strftime("%I:%M %p")
                )

            slot_start += datetime.timedelta(minutes=30)

        return available_slots

    except HttpError as error:
        print(f"Calendar API error: {error}")
        return []


def book_appointment(
    summary: str,
    date_str: str,
    time_str: str,
    customer_name: str,
    customer_phone: str,
    duration_minutes: int = 120,
) -> dict:
    try:
        service = get_calendar_service()

        try:
            date = datetime.datetime.strptime(date_str, "%d %B %Y")
        except ValueError:
            try:
                date = datetime.datetime.strptime(date_str, "%A %d %B %Y")
            except ValueError:
                date = datetime.datetime.now() + datetime.timedelta(days=1)

        try:
            time = datetime.datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            try:
                time = datetime.datetime.strptime(time_str, "%H:%M")
            except ValueError:
                time = datetime.datetime.strptime("09:00", "%H:%M")

        start_dt = date.replace(
            hour=time.hour,
            minute=time.minute,
            second=0,
            microsecond=0,
        )
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

        event = {
            "summary": f"{summary} - {customer_name}",
            "description": (
                f"Customer: {customer_name}\n"
                f"Phone: {customer_phone}\n"
                f"Service: {summary}\n"
                f"Booked via: Contractor Voice Bot"
            ),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "America/Chicago",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Chicago",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 60},
                ],
            },
        }

        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event,
        ).execute()

        return {
            "success": True,
            "event_id": created_event["id"],
            "event_link": created_event.get("htmlLink", ""),
            "summary": created_event["summary"],
            "start": start_dt.strftime("%A %d %B %Y at %I:%M %p"),
            "end": end_dt.strftime("%I:%M %p"),
        }

    except HttpError as error:
        print(f"Calendar booking error: {error}")
        return {
            "success": False,
            "error": str(error),
        }


if __name__ == "__main__":
    print("Testing Google Calendar integration...\n")

    print("Step 1: Checking available slots for tomorrow...")
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime(
        "%d %B %Y"
    )
    slots = get_available_slots(tomorrow)
    if slots:
        print(f"Available slots on {tomorrow}:")
        for slot in slots[:5]:
            print(f"  {slot}")
    else:
        print("No available slots or calendar is fully booked.")

    print("\nStep 2: Booking a test appointment...")
    result = book_appointment(
        summary="Plumbing repair",
        date_str=tomorrow,
        time_str="10:00 AM",
        customer_name="Test Customer",
        customer_phone="512-555-0199",
        duration_minutes=120,
    )

    if result["success"]:
        print(f"Booking confirmed:")
        print(f"  Event: {result['summary']}")
        print(f"  Start: {result['start']}")
        print(f"  End: {result['end']}")
        print(f"  Link: {result['event_link']}")
    else:
        print(f"Booking failed: {result['error']}")