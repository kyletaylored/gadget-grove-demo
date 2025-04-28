# gadget_celery/tasks.py

# Correctly import the app instance from the celery_app module within the package
from gadget_celery.app import app
import os
import random
import requests
import time
import logging
import subprocess
import sys
import asyncio

# Datadog tracing
from ddtrace import patch_all
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
    logger.info(f"Generating {num_sessions} simulated user sessions (API)")

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

        time.sleep(random.uniform(1, 3))

    return f"Successfully generated {successful_sessions} of {num_sessions} user sessions"


@app.task(name="traffic.simulate_browser_sessions")
def simulate_browser_sessions(num_sessions=1):
    """Simulate browser sessions using Playwright asynchronously"""
    logger.info(
        f"Simulating {num_sessions} browser sessions (headless, async)")

    async def run_session(index):
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "/app/simulate_browser.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(
                    f"[Session {index}] Completed successfully:\n{stdout.decode().strip()}")
            else:
                logger.error(
                    f"[Session {index}] Failed with error:\n{stderr.decode().strip()}")

        except Exception as e:
            logger.error(f"[Session {index}] Error running session: {e}")

    async def run_all_sessions():
        tasks = [run_session(i + 1) for i in range(num_sessions)]
        await asyncio.gather(*tasks)

    asyncio.run(run_all_sessions())

    return f"Scheduled {num_sessions} async browser sessions"


@app.task(name="traffic.schedule_generation")
def schedule_traffic_generation():
    """Schedule periodic traffic generation"""
    num_sessions = random.randint(1, 5)

    # Generate traffic - schedule the task to run asynchronously
    simulate_browser_sessions.delay(num_sessions)

    return f"Scheduled generation of {num_sessions} sessions"


# ---- Data Processing Tasks ----

@app.task(name="data.process_events")
def process_raw_events(event_type=None):
    """Process raw event files (placeholder for actual processing)"""
    logger.info(f"Processing raw events of type: {event_type}")
    return f"Processed events of type {event_type}"


@app.task(name="data.cleanup_files")
def cleanup_old_files(days=7):
    """Clean up old processed files"""
    logger.info(f"Cleaning up files older than {days} days")
    return f"Cleaned up old files"
