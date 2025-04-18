import pika
import os
import json
from datetime import datetime, UTC
from pathlib import Path

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "event_queue")
RAW_DIR = Path("/data/raw")

RAW_DIR.mkdir(parents=True, exist_ok=True)


def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        filename = RAW_DIR / f"event_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(event, f)
        print(f"[✓] Saved {filename.name}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[X] Failed to process message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)


def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print(
        f"[*] Waiting for messages on queue '{QUEUE_NAME}'. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping consumer...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
