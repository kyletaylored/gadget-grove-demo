import pika
import os
import json
from datetime import datetime, UTC
from pathlib import Path
import logging

# Datadog tracing
from ddtrace import patch_all
patch_all()

# Set up logging
FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.level = logging.INFO

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
DEFAULT_QUEUE = os.getenv("RABBITMQ_QUEUE", "event_queue")
RAW_DIR = Path("/data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# All queues to consume from
QUEUES = [
    "page_views",
    "user_events",
    "ecommerce_events",
    "analytics_events",
    DEFAULT_QUEUE  # Fallback queue
]


def save_event_to_file(event, queue_name):
    """Save an event to the appropriate directory structure"""
    # Determine event type for directory organization
    event_type = event.get("type", "unknown")
    if event_type == "custom_event" and "event" in event:
        # For custom events, use the specific event name
        event_type = event["event"]

    # Create directory structure
    event_dir = RAW_DIR / queue_name / event_type
    event_dir.mkdir(parents=True, exist_ok=True)

    # Add metadata
    event["_queue"] = queue_name
    event["_processed_at"] = datetime.now(UTC).isoformat()

    # Generate filename with timestamp
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    session_id = event.get("sessionId", event.get("session_id", "unknown"))
    filename = event_dir / f"{timestamp}_{session_id}.json"

    # Write to file
    with open(filename, "w") as f:
        json.dump(event, f, indent=2)

    return filename


def callback(ch, method, properties, body):
    """Process a message from RabbitMQ"""
    queue_name = method.routing_key

    try:
        # Parse the message
        event = json.loads(body)

        # Save to file
        filename = save_event_to_file(event, queue_name)
        logger.info(f"Saved {filename.name} from queue {queue_name}")

        # Acknowledge successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Failed to process message from {queue_name}: {e}")
        # Negative acknowledgment - message will be requeued
        ch.basic_nack(delivery_tag=method.delivery_tag)


def main():
    """Main consumer function"""
    logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT))
    channel = connection.channel()

    # Set up queues and consume from each
    for queue_name in QUEUES:
        try:
            # Declare the queue (ensure it exists)
            channel.queue_declare(queue=queue_name, durable=True)

            # Set up consumption
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback)
            logger.info(f"Set up consumption from queue: {queue_name}")
        except Exception as e:
            logger.error(f"Error setting up queue {queue_name}: {e}")

    logger.info("Starting consumption. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
