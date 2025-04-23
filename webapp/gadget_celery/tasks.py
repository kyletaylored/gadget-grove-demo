# gadget_celery/tasks.py

# Correctly import the app instance from the celery_app module within the package
from gadget_celery.app import app
import os
import random
import requests
import time
import logging
from datetime import datetime, UTC
# Ensure your utils.py is accessible, e.g., in the parent directory or same package
from utils import send_event  # Make sure utils.py is structured correctly

# Datadog tracing
from ddtrace import patch_all, tracer
patch_all()

# Setup logging
FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.level = logging.INFO

# Configuration
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://webapp:8000")
# Note: MAX_WORKERS is typically a worker configuration, not used in tasks directly
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))

# RabbitMQ queues
QUEUES = {
    "page_view": "page_views",
    "identify": "user_events",
    "logout": "user_events",
    "user_engagement": "user_events",
    "add_to_cart": "ecommerce_events",
    "purchase": "ecommerce_events",
    "product_view": "ecommerce_events",
    "checkout_error": "ecommerce_events",
    "begin_checkout": "ecommerce_events"
}

# ---- Traffic Generation Tasks ----


@app.task(name="traffic.generate_traffic")
def generate_traffic(num_sessions=1):
    """Generate simulated traffic by calling the /simulate endpoint"""
    logger.info(f"Generating {num_sessions} simulated user sessions")

    successful_sessions = 0
    for _ in range(num_sessions):
        try:
            response = requests.get(f"{WEBAPP_URL}/simulate")

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"Generated session {data['session_id']} with {len(data['events'])} events")
                successful_sessions += 1
            else:
                logger.error(
                    f"Failed to generate session: {response.status_code}")
        except Exception as e:
            logger.error(f"Error generating traffic: {e}")

        # Random delay between sessions (1-3 seconds)
        # Using uniform for float seconds, as in your original code
        time.sleep(random.uniform(1, 3))

    return f"Successfully generated {successful_sessions} of {num_sessions} user sessions"


@app.task(name="traffic.simulate_session")
def simulate_user_session():
    """Simulate a user session by generating events directly"""
    session_id = str(random.randint(10000, 99999))
    events = []

    # Generate page view event
    events.append({
        "type": "page_view",
        "url": f"{WEBAPP_URL}/",
        "path": "/",
        "title": "GadgetGrove Shop",
        "timestamp": datetime.now(UTC).isoformat(),
        "sessionId": session_id
    })

    # Send events to the appropriate queues
    for event in events:
        event_type = event.get("type")
        # Handle potential custom event type extraction if applicable
        if event_type == "custom_event" and "event" in event:
            # Assuming custom events have an 'event' field
            event_type = event["event"]

        # Determine queue name - falls back to 'analytics_events' if type not in QUEUES
        queue_name = QUEUES.get(event_type, "analytics_events")

        # Send to RabbitMQ using your utility function
        # Ensure send_event handles sending to the correct queue based on event type or queue_name
        send_event(event)  # Your send_event logic should handle routing

    return f"Generated session {session_id} with {len(events)} events"


@app.task(name="traffic.schedule_generation")
def schedule_traffic_generation():
    """Schedule periodic traffic generation"""
    # Random number of sessions to generate (1-5)
    num_sessions = random.randint(1, 5)

    # Generate traffic - schedule the task to run asynchronously
    generate_traffic.delay(num_sessions)

    return f"Scheduled generation of {num_sessions} sessions"


# ---- Data Processing Tasks ----

@app.task(name="data.process_events")
def process_raw_events(event_type=None):
    """Process raw event files (placeholder for actual processing)"""
    logger.info(f"Processing raw events of type: {event_type}")

    # You would implement actual file processing here
    # This is just a placeholder to show the task is running

    return f"Processed events of type {event_type}"


@app.task(name="data.cleanup_files")
def cleanup_old_files(days=7):
    """Clean up old processed files"""
    logger.info(f"Cleaning up files older than {days} days")

    # You would implement file cleanup logic here

    return f"Cleaned up old files"
