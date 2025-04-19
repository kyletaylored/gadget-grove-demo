from pathlib import Path
from datetime import datetime, UTC, timedelta
from fastapi import FastAPI, Request, Form, Response, Cookie, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from faker import Faker
import json
import uuid
import random
import secrets
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Realistic gadget store data ---
CATEGORIES = {
    "Smartphones": {
        "name_prefixes": ["Galaxy", "iPhone", "Pixel", "Mate", "Nova", "OnePlus", "Redmi", "Xperia"],
        "brands": ["Samsung", "Apple", "Google", "Huawei", "Xiaomi", "OnePlus", "Sony"],
        "specs": ["5G", "Ultra HD", "AMOLED", "Quad Camera", "120Hz"],
        "storage": ["64GB", "128GB", "256GB", "512GB", "1TB"],
        "colors": ["Black", "White", "Silver", "Gold", "Midnight Blue", "Graphite", "Rose Gold"],
        "price_range": (499, 1599)
    },
    "Laptops": {
        "name_prefixes": ["MacBook", "Zenbook", "ThinkPad", "XPS", "Inspiron", "Legion", "Surface", "Spectre"],
        "brands": ["Apple", "Asus", "Lenovo", "Dell", "HP", "Microsoft"],
        "specs": ["Ultra-thin", "Gaming", "2-in-1", "Business", "Creator"],
        "storage": ["256GB SSD", "512GB SSD", "1TB SSD", "2TB SSD"],
        "memory": ["8GB", "16GB", "32GB", "64GB"],
        "processors": ["Intel i5", "Intel i7", "Intel i9", "AMD Ryzen 5", "AMD Ryzen 7", "AMD Ryzen 9", "M1", "M2"],
        "colors": ["Silver", "Space Gray", "Black", "White", "Blue"],
        "price_range": (799, 2999)
    },
    "Tablets": {
        "name_prefixes": ["iPad", "Galaxy Tab", "Surface", "MatePad", "Pixel Slate", "Fire HD"],
        "brands": ["Apple", "Samsung", "Microsoft", "Huawei", "Google", "Amazon"],
        "storage": ["32GB", "64GB", "128GB", "256GB"],
        "colors": ["Silver", "Space Gray", "Gold", "Blue", "Black"],
        "price_range": (199, 1299)
    },
    "Headphones": {
        "name_prefixes": ["AirPods", "QC", "WH", "Buds", "Studio", "FreeBuds", "Elite"],
        "brands": ["Apple", "Bose", "Sony", "Samsung", "Beats", "Huawei", "Jabra"],
        "types": ["Over-ear", "In-ear", "On-ear", "True Wireless"],
        "specs": ["Noise Cancelling", "High-Res Audio", "Spatial Audio", "Waterproof"],
        "colors": ["Black", "White", "Silver", "Red", "Blue", "Pink"],
        "price_range": (69, 499)
    },
    "Smartwatches": {
        "name_prefixes": ["Apple Watch", "Galaxy Watch", "Fitbit", "Mi Band", "Versa", "Venu"],
        "brands": ["Apple", "Samsung", "Fitbit", "Xiaomi", "Garmin", "Huawei"],
        "sizes": ["40mm", "42mm", "44mm", "46mm"],
        "colors": ["Black", "Silver", "Gold", "Blue", "Red"],
        "price_range": (149, 799)
    }
}

# Create persistent but fake databases for the session
PRODUCT_DB = []
USER_SESSIONS = {}  # Store active user sessions
SESSION_COOKIE_NAME = "gadgetgrove_session"
SESSION_EXPIRY = 30  # minutes

# --- Data models ---


class CartItem(BaseModel):
    product_id: str
    quantity: int


class CheckoutRequest(BaseModel):
    name: str
    email: str
    items: List[CartItem]
    total: float


class UserSession(BaseModel):
    session_id: str
    user_id: str
    user_data: Dict[str, Any]
    created_at: datetime
    expires_at: datetime


class SessionResponse(BaseModel):
    session_id: str
    user: Dict[str, Any]


# --- Fake data generators ---
fake = Faker()

# Session management functions


def create_session():
    """Create a new user session"""
    session_id = secrets.token_urlsafe(32)
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Create user data
    user_data = {
        "id": user_id,
        "name": fake.name(),
        "email": fake.email(),
        "address": fake.address(),
        "payment_card": fake.credit_card_full(),
        "created_at": now.isoformat(),
        "last_active": now.isoformat()
    }

    # Create session
    session = UserSession(
        session_id=session_id,
        user_id=user_id,
        user_data=user_data,
        created_at=now,
        expires_at=now + timedelta(minutes=SESSION_EXPIRY)
    )

    # Store session
    USER_SESSIONS[session_id] = session

    return session


def get_session(session_id: str = Cookie(None, alias=SESSION_COOKIE_NAME)):
    """Get an existing session or create a new one"""
    now = datetime.now(UTC)

    if session_id and session_id in USER_SESSIONS:
        session = USER_SESSIONS[session_id]

        # Check if session is expired
        if now > session.expires_at:
            del USER_SESSIONS[session_id]
            return create_session()

        # Update last active time
        session.user_data["last_active"] = now.isoformat()
        session.expires_at = now + timedelta(minutes=SESSION_EXPIRY)

        return session

    # Create new session if no valid session exists
    return create_session()


def end_session(session_id: str):
    """End a user session"""
    if session_id in USER_SESSIONS:
        del USER_SESSIONS[session_id]
        return True
    return False


def generate_user(session_id: str = None):
    """Get user data from session or create new user"""
    if session_id and session_id in USER_SESSIONS:
        return USER_SESSIONS[session_id].user_data

    # Create a new session if none exists
    session = create_session()
    return session.user_data


def generate_product_name(category):
    cat_data = CATEGORIES[category]
    if "brands" in cat_data and "name_prefixes" in cat_data:
        brand = random.choice(cat_data["brands"])
        prefix = random.choice(cat_data["name_prefixes"])

        # Add some randomness to product naming
        if random.random() > 0.7:
            if "specs" in cat_data:
                spec = random.choice(cat_data["specs"])
                return f"{brand} {prefix} {spec}"
            elif "types" in cat_data:
                type_ = random.choice(cat_data["types"])
                return f"{brand} {prefix} {type_}"

        # Base product name
        if random.random() > 0.5:
            year = random.randint(2020, 2024)
            return f"{brand} {prefix} ({year})"
        else:
            model = random.choice(
                ["Pro", "Plus", "Max", "Ultra", "SE", "Lite", ""])
            return f"{brand} {prefix} {model}".strip()

    # Fallback
    return f"{random.choice(cat_data['brands'])} {random.choice(cat_data['name_prefixes'])}"


def generate_product_features(category):
    cat_data = CATEGORIES[category]
    features = {}

    if "storage" in cat_data:
        features["storage"] = random.choice(cat_data["storage"])

    if "memory" in cat_data:
        features["memory"] = random.choice(cat_data["memory"])

    if "processors" in cat_data:
        features["processor"] = random.choice(cat_data["processors"])

    if "types" in cat_data:
        features["type"] = random.choice(cat_data["types"])

    if "specs" in cat_data:
        # Add 1-3 specs
        num_specs = random.randint(1, min(3, len(cat_data["specs"])))
        features["specs"] = random.sample(cat_data["specs"], num_specs)

    if "sizes" in cat_data:
        features["size"] = random.choice(cat_data["sizes"])

    return features


def generate_product(category):
    cat_data = CATEGORIES[category]
    price_min, price_max = cat_data["price_range"]
    product_id = f"{category[:2].upper()}-{str(uuid.uuid4())[:8]}"

    # Generate a price point that seems realistic (ending in 9s)
    base_price = round(random.uniform(price_min, price_max) / 10) * 10 - 0.01

    return {
        "id": product_id,
        "name": generate_product_name(category),
        "price": base_price,
        "category": category,
        "brand": random.choice(cat_data["brands"]),
        "color": random.choice(cat_data["colors"]),
        "features": generate_product_features(category),
        "rating": round(random.uniform(3.5, 5.0), 1),
        "in_stock": random.random() > 0.1
    }


def generate_products(reload=False):
    global PRODUCT_DB
    if not PRODUCT_DB or reload:
        PRODUCT_DB = []
        # Generate a balanced number of products per category
        for category in CATEGORIES:
            # Create 3-5 products per category
            for _ in range(random.randint(3, 5)):
                PRODUCT_DB.append(generate_product(category))

    return PRODUCT_DB

# --- Routes ---


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Redirect to shop page"""
    return RedirectResponse(url="/shop")


@app.get("/shop", response_class=HTMLResponse)
def shop_ui(request: Request, session: UserSession = Depends(get_session)):
    """Main shop UI with session management"""
    products = generate_products()
    categories = list(CATEGORIES.keys())

    # Set session cookie in response
    response = templates.TemplateResponse(
        "shop.html",
        {
            "request": request,
            "user": session.user_data,
            "products": products,
            "categories": categories,
            "session_id": session.session_id
        }
    )

    # Set session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_id,
        max_age=SESSION_EXPIRY * 60,  # convert minutes to seconds
        httponly=True,
        samesite="lax"
    )

    return response


@app.get("/api/products", response_class=JSONResponse)
def get_products(category: Optional[str] = None):
    """Get products, optionally filtered by category"""
    products = generate_products()

    if category:
        products = [p for p in products if p["category"] == category]

    return {"products": products}


@app.get("/api/session", response_class=JSONResponse)
def get_current_session(session: UserSession = Depends(get_session)):
    """Get current session info"""
    return {
        "session_id": session.session_id,
        "user": session.user_data,
        "expires_at": session.expires_at.isoformat(),
        "created_at": session.created_at.isoformat()
    }


@app.post("/api/session/end", response_class=JSONResponse)
def end_current_session(session_id: str = Cookie(None, alias=SESSION_COOKIE_NAME)):
    """Manually end the current session"""
    if not session_id or session_id not in USER_SESSIONS:
        return JSONResponse(
            status_code=400,
            content={"status": "failed", "message": "No active session"}
        )

    # End the session
    success = end_session(session_id)

    # Create response
    response = JSONResponse(
        content={
            "status": "success" if success else "failed",
            "message": "Session ended" if success else "Failed to end session"
        }
    )

    # Clear the session cookie
    if success:
        response.delete_cookie(key=SESSION_COOKIE_NAME)

    return response


@app.post("/api/session/refresh", response_class=JSONResponse)
def refresh_session(session: UserSession = Depends(get_session)):
    """Refresh the current session"""
    return {
        "status": "success",
        "session_id": session.session_id,
        "user": session.user_data,
        "expires_at": session.expires_at.isoformat()
    }


# Make sure this path exists in your container
CHECKOUT_LOG = Path("/app/logs/checkout_log.jsonl")


@app.post("/checkout")
async def checkout(request: Request, session_id: str = Cookie(None, alias=SESSION_COOKIE_NAME)):
    """Process checkout and end session on success"""
    # Parse the checkout form data
    form_data = await request.json()

    # Get user from session
    user_data = {}
    if session_id and session_id in USER_SESSIONS:
        user_data = USER_SESSIONS[session_id].user_data

    # Create checkout record
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "user": {
            "id": user_data.get("id", "anonymous"),
            "name": form_data.get("name", user_data.get("name", "Anonymous")),
            "email": form_data.get("email", user_data.get("email", "anonymous@example.com"))
        },
        "items": form_data.get("items", []),
        "total": form_data.get("total", 0),
        "success": random.random() > 0.1
    }

    # Ensure the log directory exists
    CHECKOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKOUT_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    # Prepare response
    if record["success"]:
        # End session on successful checkout if requested
        end_session_after_checkout = form_data.get("end_session", False)

        response_data = {
            "status": "success",
            "message": "Order processed successfully",
            "order_id": str(uuid.uuid4()),
            "session_ended": False
        }

        # Create response
        response = JSONResponse(content=response_data)

        # End session if requested
        if end_session_after_checkout and session_id:
            if end_session(session_id):
                response_data["session_ended"] = True
                # Clear the session cookie
                response.delete_cookie(key=SESSION_COOKIE_NAME)

        return response
    else:
        return JSONResponse(
            status_code=400,
            content={
                "status": "failed",
                "reason": random.choice([
                    "Payment Declined",
                    "Insufficient Funds",
                    "Card Verification Failed",
                    "Network Error"
                ])
            }
        )


@app.get("/simulate")
def simulate():
    session_id = str(uuid.uuid4())
    products = generate_products()
    cart = []
    events = []

    events.append({"event_type": "page_view", "path": "/"})

    # Simulate a user browsing products
    for _ in range(random.randint(2, 6)):
        # Pick a random category
        category = random.choice(list(CATEGORIES.keys()))
        category_products = [p for p in products if p["category"] == category]

        if not category_products:
            continue

        product = random.choice(category_products)

        events.append({"event_type": "page_view",
                      "path": f"/category/{category}"})
        events.append({"event_type": "product_view",
                      "product_id": product["id"], "product_name": product["name"]})

        if random.random() > 0.3:
            quantity = random.randint(1, 3)
            cart.append({
                "product": product,
                "quantity": quantity
            })
            events.append({
                "event_type": "add_to_cart",
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "value": product["price"] * quantity
            })
        else:
            events.append({"event_type": "page_view", "path": "/"})

    if cart:
        total = round(sum(item["product"]["price"] *
                      item["quantity"] for item in cart), 2)
        events.append({"event_type": "begin_checkout",
                      "cart_value": total, "items_count": len(cart)})

        if random.random() > 0.2:
            events.append({
                "event_type": "purchase",
                "transaction_id": str(uuid.uuid4()),
                "value": total,
                "items": [{"id": item["product"]["id"], "name": item["product"]["name"], "quantity": item["quantity"]} for item in cart]
            })
        else:
            events.append({
                "event_type": "checkout_error",
                "reason": random.choice(["Payment Declined", "Shipping Address Invalid", "Item Out of Stock"])
            })

    return {"status": "simulated", "session_id": session_id, "events": events}
