from celery_app import celery_app
from datetime import datetime, UTC
from utils import send_event


@celery_app.task
def simulate_user_session(session_id, events):
    for event in events:
        event["timestamp"] = datetime.now(UTC).isoformat()
        event["session_id"] = session_id
        send_event(event)
