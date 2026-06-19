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
from sqlalchemy.orm import Session

from database import get_db, create_tables, Diagnosis, Product
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
        "http://127.0.0.1:5173",],
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
    skip:         int     = Query(0,  ge=0),
    limit:        int     = Query(20, ge=1, le=100),
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Return paginated scan history for the logged-in user.
    Frontend: GET /history  with  Authorization: Bearer <token>
    """
    rows = (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "diagnosis_id": r.id,
            "created_at":   r.created_at.isoformat(),
            "crop":         r.crop,
            "disease_name": r.disease_name,
            "severity":     r.severity,
            "status":       r.status,
            "confidence":   r.confidence,
        }
        for r in rows
    ]


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
            "spec":         p.spec,
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
        "spec":         product.spec,
    }