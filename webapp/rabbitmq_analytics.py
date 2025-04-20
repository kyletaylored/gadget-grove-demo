import json
import os
import aio_pika
from datetime import datetime, UTC
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# Create API router for analytics endpoints
analytics_router = APIRouter()

# Get RabbitMQ configuration from environment variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"

# Default RabbitMQ queue
DEFAULT_QUEUE = os.getenv("RABBITMQ_QUEUE", "event_queue")

# RabbitMQ connection
rabbitmq_connection = None
rabbitmq_channel = None

# Analytics event model


class AnalyticsEvent(BaseModel):
    type: str
    timestamp: str
    sessionId: Optional[str] = None
    queueName: Optional[str] = None
    userId: Optional[str] = None
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)

# Initialize RabbitMQ connection


async def initialize_rabbitmq(rabbitmq_url: str = RABBITMQ_URL):
    global rabbitmq_connection, rabbitmq_channel

    try:
        # Connect to RabbitMQ
        rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
        rabbitmq_channel = await rabbitmq_connection.channel()

        # Declare queues that we'll use
        await rabbitmq_channel.declare_queue(DEFAULT_QUEUE, durable=True)
        await rabbitmq_channel.declare_queue("page_views", durable=True)
        await rabbitmq_channel.declare_queue("user_events", durable=True)
        await rabbitmq_channel.declare_queue("ecommerce_events", durable=True)

        print(
            f"RabbitMQ connection established to {RABBITMQ_HOST}:{RABBITMQ_PORT}")
        return True
    except Exception as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return False

# Close RabbitMQ connection


async def close_rabbitmq():
    if rabbitmq_connection:
        await rabbitmq_connection.close()
        print("RabbitMQ connection closed")

# Analytics endpoint to receive events


@analytics_router.post("/api/analytics")
async def receive_analytics_event(request: Request):
    # Parse the event data
    event_data = await request.json()

    # Add server timestamp
    event_data["server_timestamp"] = datetime.now(UTC).isoformat()

    # Add client IP
    event_data["client_ip"] = request.client.host

    # Add user agent
    event_data["user_agent"] = request.headers.get("user-agent", "")

    # Determine the appropriate queue based on the event type
    queue_name = event_data.get("queueName", DEFAULT_QUEUE)

    # Route specific event types to appropriate queues
    event_type = event_data.get("type", "")
    if event_type == "page_view":
        queue_name = "page_views"
    elif event_type in ["identify", "user_engagement", "logout"]:
        queue_name = "user_events"
    elif event_type in ["purchase", "add_to_cart", "checkout", "product_view"]:
        queue_name = "ecommerce_events"

    # Send the event to RabbitMQ
    if rabbitmq_channel:
        try:
            await rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event_data).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name
            )
            return {"status": "success", "queue": queue_name}
        except Exception as e:
            print(f"Error sending event to RabbitMQ: {e}")
            return {"status": "error", "message": f"RabbitMQ error: {str(e)}"}
    else:
        # If RabbitMQ is not connected, return an error
        return {"status": "error", "message": "RabbitMQ connection not available"}

# Endpoint to get analytics stats (for admin/debugging)


@analytics_router.get("/api/analytics/stats")
async def get_analytics_stats():
    """Get statistics about the analytics system"""
    if not rabbitmq_channel:
        return {"status": "error", "message": "RabbitMQ connection not available"}

    # Get queue information
    queues = [DEFAULT_QUEUE, "page_views", "user_events", "ecommerce_events"]
    queue_stats = {}

    for queue_name in queues:
        try:
            queue = await rabbitmq_channel.declare_queue(queue_name, passive=True)
            queue_stats[queue_name] = {
                "message_count": queue.declaration_result.message_count,
                "consumer_count": queue.declaration_result.consumer_count
            }
        except Exception as e:
            queue_stats[queue_name] = {"error": str(e)}

    return {
        "status": "success",
        "stats": {
            "queues": queue_stats,
            "timestamp": datetime.now(UTC).isoformat()
        }
    }
