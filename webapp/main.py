from fastapi import FastAPI
from worker import simulate_user_session
import uuid
import random

app = FastAPI()


@app.get("/")
def root():
    return {"status": "OK", "message": "Welcome to GadgetGrove Data Pipeline"}


@app.get("/simulate")
def simulate():
    session_id = str(uuid.uuid4())
    category = random.choice(["Smartphones", "Laptops", "Audio"])
    product_id = f"{category[:2].upper()}{random.randint(100, 999)}"
    price = round(random.uniform(100, 2000), 2)

    events = [
        {"event_type": "page_view", "path": "/"},
        {"event_type": "page_view", "path": f"/category/{category}"},
        {"event_type": "product_view", "product_id": product_id},
        {"event_type": "add_to_cart", "product_id": product_id, "value": price},
        {"event_type": "begin_checkout", "cart_value": price},
    ]

    if random.random() > 0.1:
        events.append({"event_type": "purchase",
                      "transaction_id": str(uuid.uuid4()), "value": price})
    else:
        events.append({"event_type": "checkout_error",
                      "reason": "Payment Declined"})

    simulate_user_session.delay(session_id, events)

    return {"status": "simulation triggered", "session_id": session_id, "events_generated": len(events)}


@app.get("/results")
def results():
    return {"status": "placeholder", "message": "Analytics endpoint coming soon."}
