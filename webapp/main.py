from pathlib import Path
from datetime import datetime, UTC
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from faker import Faker
import json
import uuid
import random

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Fake data generators ---
fake = Faker()


def generate_user():
    return {
        "id": str(uuid.uuid4()),
        "name": fake.name(),
        "email": fake.email(),
        "address": fake.address(),
        "payment_card": fake.credit_card_full()
    }


def generate_product(category):
    colors = ["Red", "Blue", "Black", "Silver", "Green"]
    sizes = ["Small", "Medium", "Large", "XL"]
    return {
        "id": f"{category[:2].upper()}-{fake.uuid4()[:8]}",
        "name": fake.catch_phrase(),
        "price": round(random.uniform(25, 2000), 2),
        "category": category,
        "color": random.choice(colors),
        "size": random.choice(sizes)
    }


def generate_products(n=5):
    categories = [fake.word().title() for _ in range(3)]
    products = []
    for _ in range(n):
        cat = random.choice(categories)
        products.append(generate_product(cat))
    return products

# --- Routes ---


@app.get("/shop", response_class=HTMLResponse)
def shop_ui(request: Request):
    user = generate_user()
    products = generate_products()
    return templates.TemplateResponse("shop.html", {"request": request, "user": user, "products": products})


# Make sure this path exists in your container
CHECKOUT_LOG = Path("/app/logs/checkout_log.jsonl")


@app.post("/checkout")
def fake_checkout(
    product_id: str = Form(...),
    value: float = Form(...),
    name: str = Form(...),
    email: str = Form(...)
):
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "user": {"name": name, "email": email},
        "product_id": product_id,
        "value": value,
        "success": random.random() > 0.1
    }

    CHECKOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKOUT_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    if record["success"]:
        return {"status": "success"}
    else:
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "Payment Declined"})


@app.get("/simulate")
def simulate():
    session_id = str(uuid.uuid4())
    cart = []
    events = []

    events.append({"event_type": "page_view", "path": "/"})

    for _ in range(random.randint(1, 5)):
        category = fake.word().title()
        product = generate_product(category)

        events.append({"event_type": "page_view",
                      "path": f"/category/{category}"})
        events.append({"event_type": "product_view",
                      "product_id": product["id"], "product_name": product["name"]})

        if random.random() > 0.3:
            cart.append(product)
            events.append({"event_type": "add_to_cart",
                          "product_id": product["id"], "value": product["price"]})
        else:
            events.append({"event_type": "page_view", "path": "/"})

    if cart:
        total = round(sum(p["price"] for p in cart), 2)
        events.append({"event_type": "begin_checkout", "cart_value": total})

        if random.random() > 0.1:
            events.append({"event_type": "purchase", "transaction_id": str(
                uuid.uuid4()), "value": total})
        else:
            events.append({"event_type": "checkout_error",
                          "reason": "Payment Declined"})

    return {"status": "simulated", "session_id": session_id, "events": events}
