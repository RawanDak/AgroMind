"""
main.py  —  AgroMind Backend  (PostgreSQL edition)
===================================================
Replaces backend/main.py in RawanDak/AgroMind (backend branch).

Pipeline:
  1. Frontend uploads leaf image  →  POST /diagnose
  2. GPT-4.1-mini vision          →  crop, disease, symptoms
  3. RAG (TF-IDF on Excel)        →  matched products
  4. GPT-4.1-mini chat            →  treatment guide
  5. Diagnosis saved to PostgreSQL
  6. Merged JSON returned to frontend

Only ONE env key needed for AI:
  OPENAI_API_KEY=sk-...

Database:
  DATABASE_URL=postgresql://user:pass@host:5432/agromind
  SECRET_KEY=your-jwt-secret

Run:
  pip install -r requirements.txt
  python ingest.py       # once — builds product_index.pkl
  python seed_db.py      # once — loads products into PostgreSQL
  uvicorn main:app --reload --port 8000
"""

import os
import json
import uuid
import base64
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, create_tables, Diagnosis, Product, CartItem, Order, OrderItem
from auth import router as auth_router, get_current_user, User, SECRET_KEY, ALGORITHM
from query import DiseaseRAG, CLASS_MAP, _healthy_response
from jose import JWTError, jwt

# ── Optional auth helper ──────────────────────────────────────────────────────
# Returns the User if a valid token is sent, or None for guest requests.
# Does NOT raise 401 — allows unauthenticated access to /diagnose.
_bearer = HTTPBearer(auto_error=False)

def get_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    
    if credentials is None:
        return None

    try:
        payload  = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="AgroMind API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://98.80.119.7:5173",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup (safe — skips if already exist)
create_tables()

# Auth routes: /auth/register, /auth/login, /auth/me
app.include_router(auth_router)

# One OpenAI client — used for vision AND treatment generation
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# RAG engine — loads product_index.pkl once
rag = DiseaseRAG()


# ─────────────────────────────────────────────────────────────────────────────
#  VISION
# ─────────────────────────────────────────────────────────────────────────────
def run_vision(base64_image: str) -> dict:
    """Send the leaf image to GPT-4.1-mini — unchanged from original main.py."""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """Analyze this crop image.
Return ONLY valid JSON. Do not use markdown. Do not include any text outside the JSON.

{
  "crop": "string",
  "disease_name": "string",
  "growth_stage": "string",
  "confidence": "percentage",
  "explanation": "string",
  "disease_type": "fungal | bacterial | viral | pest | nutrient deficiency | unknown",
  "spread_rate": "slow | moderate | fast",
  "severity_score": 0,
  "severity": "Low | Medium | High",
  "symptoms": ["symptom 1", "symptom 2", "symptom 3"]
}

Instructions:
- severity_score must be an integer from 0 to 100 based only on visible disease damage.
- Use 0-29 = Low, 30-69 = Medium, 70-100 = High.
- Make your best estimate of the crop type.
- Make your best estimate of the growth stage.
- Do NOT use "unknown" unless the image contains no visible plant.
- If uncertain, provide your most likely guess and lower the confidence score.
- Use visual clues such as leaf shape, fruit, flowers, stem structure, and plant size."""
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }
        ]
    )
    return json.loads(response.output_text)


def match_class_label(crop: str, disease: str) -> str | None:
    """Match GPT vision crop+disease to a CLASS_MAP label (exact then fuzzy)."""
    crop_l    = crop.lower().strip()
    disease_l = disease.lower().strip()
    for label, info in CLASS_MAP.items():
        if (info["crop"].lower() == crop_l
                and (info.get("disease") or "").lower() == disease_l):
            return label
    for label, info in CLASS_MAP.items():
        if info["crop"].lower() == crop_l:
            label_disease = (info.get("disease") or "").lower()
            if any(w in label_disease for w in disease_l.split() if len(w) > 3):
                return label
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AgroMind API is running"}


@app.post("/diagnose")
async def diagnose(
    file:         UploadFile     = File(...),
    db:           Session        = Depends(get_db),
    current_user: User = Depends(get_user),
):
    """
    Main endpoint — upload a leaf image, get full diagnosis back.

    To link the scan to a user account, send the Authorization header:
        Authorization: Bearer <token>

    Response fields:
      Vision    : crop, disease_name, growth_stage, confidence,
                  explanation, disease_type, spread_rate, severity, symptoms
      RAG + GPT : status, pathogen, summary, severity (refined),
                  treatment, recommended_products, prevention
      DB        : diagnosis_id  (use this to fetch from /history)
    """
    try:
        # ── Step 1: read image ────────────────────────────────────────────────
        image_bytes  = await file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # ── Step 2: GPT-4.1-mini vision ──────────────────────────────────────
        vision  = run_vision(base64_image)
        crop    = vision.get("crop",         "unknown")
        disease = vision.get("disease_name", "unknown")

        # ── Step 3: healthy plant — no extra GPT call needed ─────────────────
        if disease.lower() in ("healthy", "none", "no disease", "unknown"):
            rag_result = _healthy_response(crop)
        else:
            # ── Step 4: build vision context for GPT treatment prompt ─────────
            vision_context = {
                "symptoms":    vision.get("symptoms", []),
                "explanation": vision.get("explanation", ""),
                "severity":    vision.get("severity", ""),
                "type":        vision.get("disease_type", ""),
            }

            # ── Step 5: RAG — pinned products + vector search ─────────────────
            class_label = match_class_label(crop, disease)
            if class_label:
                rag_result = rag.query_by_class(class_label, max_products=3, use_llm=True)
            else:
                rag_result = rag.query(
                    crop=crop, disease=disease, max_products=3,
                    use_llm=True, vision_context=vision_context,
                )

        # ── Step 6: build final response ─────────────────────────────────────
        result = {
            "crop":         vision.get("crop"),
            "disease_name": vision.get("disease_name"),
            "growth_stage": vision.get("growth_stage"),
            "confidence":   vision.get("confidence"),
            "explanation":  vision.get("explanation"),
            "disease_type": vision.get("disease_type"),
            "spread_rate":  vision.get("spread_rate"),
            "severity_score": vision.get("severity_score"),
            "symptoms":     vision.get("symptoms", []),
            "status":               rag_result.get("status",   "diseased"),
            "pathogen":             rag_result.get("pathogen", ""),
            "summary":              rag_result.get("summary",  ""),
            "severity":             vision.get("severity"),
            "treatment":            rag_result.get("treatment",            []),
            "recommended_products": rag_result.get("recommended_products", []),
            "prevention":           rag_result.get("prevention",           []),
        }

        # ── Step 7: save diagnosis to PostgreSQL ──────────────────────────────
        diagnosis_id = str(uuid.uuid4())
        db_diagnosis = Diagnosis(
            id           = diagnosis_id,
            user_id      = current_user.id if current_user else None,
            crop         = result.get("crop"),
            disease_name = result.get("disease_name"),
            growth_stage = result.get("growth_stage"),
            confidence   = result.get("confidence"),
            disease_type = result.get("disease_type"),
            spread_rate  = result.get("spread_rate"),
            severity     = result.get("severity"),
            symptoms     = result.get("symptoms"),
            explanation  = result.get("explanation"),
            status       = result.get("status"),
            pathogen     = result.get("pathogen"),
            summary      = result.get("summary"),
            treatment    = result.get("treatment"),
            prevention   = result.get("prevention"),
            recommended_products = result.get("recommended_products"),
        )
        db.add(db_diagnosis)
        db.commit()

        result["diagnosis_id"] = diagnosis_id
        return result

    except Exception as error:
        return {
            "crop": "unknown", "disease_name": "unknown",
            "growth_stage": "unknown", "confidence": "0%",
            "explanation": f"Error: {str(error)}", "disease_type": "unknown",
            "spread_rate": "unknown", "severity": "unknown", "symptoms": [],
            "status": "error", "pathogen": "", "summary": "",
            "treatment": [], "recommended_products": [], "prevention": [],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  HISTORY  (requires login)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/history")
def get_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sort: str = Query("newest")
):
    query = db.query(Diagnosis).filter(
        Diagnosis.user_id == current_user.id
    )

    total = query.count()

    order_by_clause = (
    Diagnosis.created_at.asc()
    if sort == "oldest"
    else Diagnosis.created_at.desc()
)

    rows = (
    query
    .order_by(order_by_clause)
    .offset(skip)
    .limit(limit)
    .all()
)

    return {
        "items": [
            {
                "diagnosis_id": r.id,
                "created_at": r.created_at.isoformat(),
                "crop": r.crop,
                "disease_name": r.disease_name,
                "severity": r.severity,
                "status": r.status,
                "confidence": r.confidence,
            }
            for r in rows
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.get("/history/{diagnosis_id}")
def get_diagnosis(
    diagnosis_id: str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Return the full saved result for one scan."""
    row = db.query(Diagnosis).filter(
        Diagnosis.id      == diagnosis_id,
        Diagnosis.user_id == current_user.id,
    ).first()
    if not row:
        return {"error": "Diagnosis not found"}
    return {
        "diagnosis_id":       row.id,
        "created_at":         row.created_at.isoformat(),
        "crop":               row.crop,
        "disease_name":       row.disease_name,
        "growth_stage":       row.growth_stage,
        "confidence":         row.confidence,
        "explanation":        row.explanation,
        "disease_type":       row.disease_type,
        "spread_rate":        row.spread_rate,
        "severity":           row.severity,
        "symptoms":           row.symptoms,
        "status":             row.status,
        "pathogen":           row.pathogen,
        "summary":            row.summary,
        "treatment":          row.treatment,
        "recommended_products": row.recommended_products,
        "prevention":         row.prevention,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    """Browse full product catalog from the database."""
    products = db.query(Product).all()
    return [
        {
            "product_id":   p.product_id,
            "name":         p.name,
            "product_type": p.product_type,
            "crops":        p.crops,
            "ingredients":  p.ingredients,
            "price":         p.price,
        }
        for p in products
    ]


@app.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get one product by ID."""
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return {"error": "Product not found"}
    return {
        "product_id":   product.product_id,
        "name":         product.name,
        "product_type": product.product_type,
        "crops":        product.crops,
        "ingredients":  product.ingredients,
        "usage":        product.usage,
        "dilution":     product.dilution,
        "price":         product.price,
    }
# ─────────────────────────────────────────────────────────────────────────────
#  CART  (requires login)
# ─────────────────────────────────────────────────────────────────────────────
 
class CartAddRequest(BaseModel):
    product_id: str
    quantity:   int = 1
 
 
class CartUpdateRequest(BaseModel):
    quantity: int
 
 
def _cart_row(item: CartItem) -> dict:
    product = item.product
    return {
        "id":           item.id,
        "product_id":   item.product_id,
        "name":         product.name if product else None,
        "price":        product.price if product else None,
        "quantity":     item.quantity,
        "subtotal":     (product.price or 0) * item.quantity if product else None,
        "added_at":     item.added_at.isoformat(),
    }
 
 
@app.get("/cart")
def get_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return everything currently in the logged-in user's cart."""
    rows = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    items = [_cart_row(r) for r in rows]
    return {
        "items": items,
        "total": sum(i["subtotal"] or 0 for i in items),
    }
 
 
@app.post("/cart/add")
def add_to_cart(
    body: CartAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a product to the cart, or bump quantity if it's already there."""
    product = db.query(Product).filter(Product.product_id == body.product_id).first()
    if not product:
        return {"error": "Product not found"}
 
    existing = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == body.product_id,
    ).first()
 
    if existing:
        existing.quantity += body.quantity
    else:
        existing = CartItem(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            product_id=body.product_id,
            quantity=body.quantity,
        )
        db.add(existing)
 
    db.commit()
    db.refresh(existing)
    return _cart_row(existing)
 
 
@app.patch("/cart/{product_id}")
def update_cart_item(
    product_id: str,
    body: CartUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the quantity for one product in the cart (removes it if quantity <= 0)."""
    item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == product_id,
    ).first()
    if not item:
        return {"error": "Item not in cart"}
 
    if body.quantity <= 0:
        db.delete(item)
        db.commit()
        return {"removed": product_id}
 
    item.quantity = body.quantity
    db.commit()
    db.refresh(item)
    return _cart_row(item)
 
 
@app.delete("/cart/{product_id}")
def remove_from_cart(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove one product from the cart entirely."""
    item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == product_id,
    ).first()
    if not item:
        return {"error": "Item not in cart"}
    db.delete(item)
    db.commit()
    return {"removed": product_id}
 
 
@app.delete("/cart")
def clear_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Empty the whole cart."""
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return {"cleared": True}
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  ORDERS  (requires login)
# ─────────────────────────────────────────────────────────────────────────────
 
def _order_row(order: Order) -> dict:
    return {
        "order_id":    order.id,
        "created_at":  order.created_at.isoformat(),
        "status":      order.status,
        "total_price": order.total_price,
        "items": [
            {
                "product_id": i.product_id,
                "name":       i.product.name if i.product else None,
                "quantity":   i.quantity,
                "price":      i.price_at_purchase,
                "subtotal":   (i.price_at_purchase or 0) * i.quantity,
            }
            for i in order.items
        ],
    }
 
 
@app.post("/orders/checkout")
def checkout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Turn everything in the cart into a completed Order, snapshotting
    each product's current price, then empty the cart.
    """
    cart_rows = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    if not cart_rows:
        return {"error": "Cart is empty"}
 
    order = Order(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        status="completed",
    )
    db.add(order)
 
    total = 0.0
    for cart_item in cart_rows:
        price = cart_item.product.price if cart_item.product else 0
        total += (price or 0) * cart_item.quantity
        db.add(OrderItem(
            id=str(uuid.uuid4()),
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_purchase=price,
        ))
        db.delete(cart_item)
 
    order.total_price = total
    db.commit()
    db.refresh(order)
    return _order_row(order)
 
 
@app.get("/orders")
def get_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Purchase history for the logged-in user, newest first."""
    rows = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_order_row(o) for o in rows]
 
 
@app.get("/orders/{order_id}")
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One order's full detail."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id,
    ).first()
    if not order:
        return {"error": "Order not found"}
    return _order_row(order)