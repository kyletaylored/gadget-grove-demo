from celery_app import celery_app
import json
import pika
import os
from datetime import datetime, UTC

queue_name = os.getenv("RABBITMQ_QUEUE", "event_queue")


def publish_event(event_data):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.getenv("RABBITMQ_HOST", "rabbitmq")))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=json.dumps(event_data),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


@celery_app.task
def simulate_user_session(session_id, events):
    for event in events:
        event["timestamp"] = datetime.now(UTC).isoformat()
        event["session_id"] = session_id
        publish_event(event)
