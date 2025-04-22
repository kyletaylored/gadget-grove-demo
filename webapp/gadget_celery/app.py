# gadget_celery/celery_app.py

import os
from celery import Celery

# Datadog tracing
from ddtrace import patch_all
patch_all()

# Create the app
# The first argument 'gadgetgrove' is the main module name, often the package name.
# The include parameter tells Celery where to find task modules.
app = Celery(
    "gadgetgrove",
    # Tell Celery to load tasks from this module
    include=['gadget_celery.tasks']
)

# Configure broker
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
# Ensure correct username and password if not guest/guest
# For a production environment, use a secret management system for credentials
BROKER_URL = f"amqp://guest:guest@{RABBITMQ_HOST}:{RABBITMQ_PORT}//"
app.conf.broker_url = BROKER_URL

# Task routing and beat schedule
app.conf.task_routes = {
    'traffic.*': {'queue': 'traffic_generation'},
    'data.*': {'queue': 'data_processing'},
}

app.conf.beat_schedule = {
    'generate-traffic-every-minute': {
        'task': 'traffic.schedule_generation',  # Ensure this matches the task name
        'schedule': 60.0,
    },
    # Example of a task with arguments if needed
    # 'cleanup-old-files-daily': {
    #     'task': 'data.cleanup_files',
    #     'schedule': crontab(hour=0, minute=0), # Requires celery[extra] or kombu
    #     'args': (14,) # Clean up files older than 14 days
    # },
}

# Optional: Other configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',  # Set a timezone
    enable_utc=True,
)

# This block is mainly for development/testing to run the worker directly
# In production/Docker, you'll use the 'celery -A ... worker' command
if __name__ == '__main__':
    app.start()
