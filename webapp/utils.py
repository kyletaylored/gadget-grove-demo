import pika
import json
import os

QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "event_queue")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


def send_event(event):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(event),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()
