from celery import Celery
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
BROKER_URL = f"amqp://guest:guest@{RABBITMQ_HOST}:{RABBITMQ_PORT}//"

celery_app = Celery("gadgetgrove", broker=BROKER_URL)
