"""
query.py  —  AgroMind RAG engine  (database-first edition)
===========================================================
Uses ONLY OpenAI (gpt-4.1-mini) — one key, one service.

Product lookup order (two layers):
  Layer 1 — DB JOIN on disease_products table
             Exact, curated, 201 mappings across 20 diseases.
             Fast (microseconds). Always preferred.
  Layer 2 — TF-IDF vector search on product_index.pkl
             Approximate fallback for diseases NOT in the DB table.
             Catches new diseases the mapping CSV doesn't cover yet.

Flow:
  GPT-4.1-mini vision → crop + disease
      ↓
  Layer 1: DB lookup  →  matched products   (if found → skip layer 2)
      ↓  (if empty)
  Layer 2: TF-IDF search → matched products
      ↓
  GPT-4.1-mini chat   →  treatment guide using catalog data
      ↓
  Structured JSON     →  frontend

Requires:
  OPENAI_API_KEY     in .env
  DATABASE_URL       in .env
  product_index.pkl  built by:  python ingest.py
  DB seeded by:                 python seed_db.py
"""

import json
import os
import pickle
import re
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# DB session for Layer 1 lookups
from sqlalchemy.orm import Session
from database import SessionLocal, DiseaseProduct, Product, Disease

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
INDEX_PATH   = "product_index.pkl"
TOP_K        = 8      # candidates from TF-IDF before re-ranking
MAX_PRODUCTS = 3      # products returned in final response
GPT_MODEL    = "gpt-4.1-mini"


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set. Add it to your .env file.")
    return OpenAI(api_key=api_key)


def _get_db() -> Session:
    """Open a one-off DB session for RAG lookups (not a FastAPI request)."""
    return SessionLocal()


# ─────────────────────────────────────────────────────────────────────────────
#  CLASS → CROP / DISEASE  (all 15 PlantVillage classes)
# ─────────────────────────────────────────────────────────────────────────────
CLASS_MAP: dict[str, dict] = {
    "Pepper__bell___Bacterial_spot":               {"crop": "Pepper", "disease": "Bacterial Spot",         "healthy": False},
    "Pepper__bell___healthy":                      {"crop": "Pepper", "disease": None,                     "healthy": True},
    "Potato___Early_blight":                       {"crop": "Potato", "disease": "Early Blight",           "healthy": False},
    "Potato___Late_blight":                        {"crop": "Potato", "disease": "Late Blight",            "healthy": False},
    "Potato___healthy":                            {"crop": "Potato", "disease": None,                     "healthy": True},
    "Tomato_Bacterial_spot":                       {"crop": "Tomato", "disease": "Bacterial Spot",         "healthy": False},
    "Tomato_Early_blight":                         {"crop": "Tomato", "disease": "Early Blight",           "healthy": False},
    "Tomato_Late_blight":                          {"crop": "Tomato", "disease": "Late Blight",            "healthy": False},
    "Tomato_Leaf_Mold":                            {"crop": "Tomato", "disease": "Leaf Mold",              "healthy": False},
    "Tomato_Septoria_leaf_spot":                   {"crop": "Tomato", "disease": "Septoria Leaf Spot",     "healthy": False},
    "Tomato_Spider_mites_Two_spotted_spider_mite": {"crop": "Tomato", "disease": "Spider Mites",           "healthy": False},
    "Tomato__Target_Spot":                         {"crop": "Tomato", "disease": "Target Spot",            "healthy": False},
    "Tomato__Tomato_YellowLeaf__Curl_Virus":       {"crop": "Tomato", "disease": "Yellow Leaf Curl Virus", "healthy": False},
    "Tomato__Tomato_mosaic_virus":                 {"crop": "Tomato", "disease": "Mosaic Virus",           "healthy": False},
    "Tomato_healthy":                              {"crop": "Tomato", "disease": None,                     "healthy": True},
}

# ─────────────────────────────────────────────────────────────────────────────
#  PATHOGEN FACTS  (fed to GPT to anchor the treatment guide)
# ─────────────────────────────────────────────────────────────────────────────
PATHOGEN_FACTS: dict[str, str] = {
    "bacterial spot":         "Xanthomonas spp. — bacterial, spreads via water splash and contact",
    "early blight":           "Alternaria solani — fungal, produces concentric ring lesions on older leaves",
    "late blight":            "Phytophthora infestans — oomycete, spreads explosively in cool humid conditions",
    "leaf mold":              "Passalora fulva — fungal, greenhouse disease favoured by humidity above 85%",
    "septoria leaf spot":     "Septoria lycopersici — fungal, small circular spots starting on lower leaves",
    "spider mites":           "Tetranychus urticae — arthropod pest, stippling and bronzing in hot dry weather",
    "target spot":            "Corynespora cassiicola — fungal, concentric brown rings on all above-ground parts",
    "yellow leaf curl virus": "TYLCV — begomovirus transmitted by Bemisia tabaci whitefly, no cure once infected",
    "mosaic virus":           "Tomato Mosaic Virus (ToMV) — contact and aphid transmitted, mosaic mottling",
    "downy mildew":           "Peronospora / Plasmopara spp. — oomycete, yellow patches on upper leaf, grey mould below",
    "powdery mildew":         "Erysiphe / Leveillula spp. — fungal, white powdery coating on leaf surface",
    "anthracnose":            "Colletotrichum spp. — fungal, dark sunken lesions on fruit and stems",
    "gray mold":              "Botrytis cinerea — fungal, grey fuzzy growth, thrives in cool humid conditions",
    "root rot":               "Phytophthora / Fusarium / Pythium spp. — fungal/oomycete, crown and root decay",
    "wilt":                   "Fusarium oxysporum / Verticillium spp. — soil-borne fungal, vascular wilting",
    "damping-off":            "Pythium / Rhizoctonia spp. — seedling stems collapse at soil level",
    "aphids":                 "Aphididae — soft-bodied sucking insects, vector for multiple viruses",
    "whiteflies":             "Bemisia tabaci / Trialeurodes vaporariorum — vector for TYLCV and other viruses",
    "thrips":                 "Thysanoptera — minute insects causing silvery scarring and virus transmission",
    "rust":                   "Puccinia / Phakopsora spp. — fungal, orange-brown pustules on leaf undersides",
    "leaf spot":              "Various fungal pathogens — circular spots with defined margins",
    "scab":                   "Venturia / Streptomyces spp. — fungal/bacterial, rough corky lesions on fruit",
    "soft rot":               "Pectobacterium / Dickeya spp. — bacterial, foul-smelling tissue collapse",
    "black spot":             "Alternaria / Diplocarpon spp. — fungal, black lesions with yellow halo",
    "purple blotch":          "Alternaria porri — fungal, purple-brown lesions on onion and allium leaves",
    "nematodes":              "Root-knot nematodes (Meloidogyne spp.) — microscopic soil worms causing root galls",
}


# ─────────────────────────────────────────────────────────────────────────────
#  DISEASE NAME NORMALISER
#  Maps GPT vision free-text → canonical disease name used in DB
# ─────────────────────────────────────────────────────────────────────────────
def _normalise_disease(disease: str) -> str:
    """
    Lower-case and strip the GPT vision disease name, then try to
    match it to a known canonical name.

    Examples:
      "Early Blight"           → "early blight"
      "Powdery Mildew Disease" → "powdery mildew"
      "Spider Mite Infestation"→ "spider mites"
    """
    d = disease.lower().strip()

    # Direct known alias table
    aliases = {
        "early blight":               "early blight",
        "late blight":                "late blight",
        "bacterial spot":             "bacterial spot",
        "leaf mold":                  "leaf mold",
        "leaf mould":                 "leaf mold",
        "septoria leaf spot":         "leaf spot",
        "septoria":                   "leaf spot",
        "target spot":                "leaf spot",
        "spider mite":                "spider mites",
        "spider mites":               "spider mites",
        "two-spotted spider mite":    "spider mites",
        "yellow leaf curl":           "yellow leaf curl virus",
        "yellow leaf curl virus":     "yellow leaf curl virus",
        "tylcv":                      "yellow leaf curl virus",
        "mosaic virus":               "wilt",          # no mosaic in CSV — closest pest
        "tomato mosaic virus":        "wilt",
        "powdery mildew":             "powdery mildew",
        "downy mildew":               "downy mildew",
        "anthracnose":                "anthracnose",
        "gray mold":                  "gray mold",
        "grey mold":                  "gray mold",
        "botrytis":                   "gray mold",
        "root rot":                   "root rot",
        "wilt":                       "wilt",
        "fusarium wilt":              "wilt",
        "damping-off":                "damping-off",
        "damping off":                "damping-off",
        "aphids":                     "aphids",
        "aphid":                      "aphids",
        "whitefly":                   "whiteflies",
        "whiteflies":                 "whiteflies",
        "thrips":                     "thrips",
        "rust":                       "rust",
        "leaf spot":                  "leaf spot",
        "scab":                       "scab",
        "apple scab":                 "scab",
        "soft rot":                   "soft rot",
        "black spot":                 "black spot",
        "purple blotch":              "purple blotch",
        "nematodes":                  "nematodes",
        "nematode":                   "nematodes",
    }

    if d in aliases:
        return aliases[d]

    # Partial match — check if any alias key is a substring of d
    for key, canonical in aliases.items():
        if key in d:
            return canonical

    return d   # unchanged — DB lookup will return empty, RAG takes over


# ─────────────────────────────────────────────────────────────────────────────
#  HEALTHY RESPONSE
# ─────────────────────────────────────────────────────────────────────────────
def _healthy_response(crop: str) -> dict:
    return {
        "crop":                 crop,
        "disease":              None,
        "status":               "healthy",
        "pathogen":             None,
        "summary":              f"Your {crop} plant appears healthy. No disease detected.",
        "severity":             "None",
        "treatment":            [],
        "recommended_products": [],
        "prevention": [
            "Continue regular monitoring — inspect leaves weekly",
            "Water at the plant base; avoid wetting foliage",
            "Ensure proper plant spacing for good air circulation",
            "Rotate crops each season to prevent soil-borne disease buildup",
            "Remove and destroy any fallen or dead leaves promptly",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GPT-4.1-mini  TREATMENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_treatment(
    crop: str,
    disease: str,
    pathogen_fact: str,
    products: list[dict],
    vision_context: dict | None = None,
) -> dict:
    """
    Calls GPT-4.1-mini chat to write a treatment guide.
    Uses catalog product data (ingredients, dilution, usage) as context.
    Optionally enriched with GPT vision symptoms.
    """
    product_lines = []
    for p in products:
        product_lines.append(
            f"  - Product: {p['name']} (ID: {p['product_id']})\n"
            f"    Type: {p['product_type']}\n"
            f"    Active ingredients: {p['ingredients'] or 'not specified'}\n"
            f"    Usage instructions: {p['raw_usage'] or p['usage'] or 'follow label'}\n"
            f"    Dilution ratio: {p['dilution'] or 'see label'}\n"
            f"    Pack size: {p['spec'] or 'varies'}"
        )
    products_text = "\n\n".join(product_lines) or "No matching products found."

    vision_block = ""
    if vision_context:
        symptoms_text = "\n".join(
            f"  • {s}" for s in (vision_context.get("symptoms") or [])
        )
        vision_block = (
            "\n=== VISUAL SYMPTOMS SEEN IN THE PHOTO ===\n"
            f"Disease type : {vision_context.get('type', 'unknown')}\n"
            f"Severity     : {vision_context.get('severity', 'unknown')}\n"
            f"Explanation  : {vision_context.get('explanation', 'N/A')}\n"
            f"Symptoms     :\n{symptoms_text or '  • Not specified'}\n"
            "\nReference these symptoms in your summary.\n"
        )

    prompt = f"""You are an expert agricultural plant pathologist and crop protection advisor.
A farmer uploaded a photo and the AI detected a disease.

=== DETECTION ===
Crop     : {crop}
Disease  : {disease}
Pathogen : {pathogen_fact}
{vision_block}
=== CATALOG PRODUCTS AVAILABLE ===
{products_text}

=== TASK ===
Write a complete practical treatment guide for a farmer with no agronomic training.
- Mention the visible symptoms in your summary.
- Use the catalog usage instructions (dilution ratios) for product_guidance.
- Only use products listed above — never invent products.
- You MUST return exactly one product_guidance object for every product listed in CATALOG PRODUCTS AVAILABLE.
- Every product_guidance object MUST include the exact product_id from the catalog.
- Do not skip any product.

Respond ONLY with valid JSON — no markdown, no text outside the JSON:
{{
  "pathogen": "<full pathogen name and type>",
  "summary": "<2-3 plain-language sentences referencing visible symptoms>",
  "severity": "<Low | Medium | High | Critical>",
  "treatment": ["<step 1>", "<step 2>", "<step 3>", "<step 4>", "<step 5>"],
  "product_guidance": [
    {{
      "product_id": "<exact id>",
      "name": "<exact product name>",
      "how_to_use": "<specific instructions for {disease} on {crop}>",
      "frequency": "<e.g. every 7 days for 2-3 applications>",
      "caution": "<one safety or resistance-management note>"
    }}
  ],
  "prevention": ["<tip 1>", "<tip 2>", "<tip 3>"]
}}"""

    client = _get_client()
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise agricultural advisor. "
                    "Always respond with valid JSON only. "
                    "Never add markdown fences or text outside the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1200,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "pathogen":  pathogen_fact,
            "summary":   f"{disease} detected on {crop}. Consult a local agronomist.",
            "severity":  "Medium",
            "treatment": [
                "Remove infected plant parts immediately",
                "Apply the recommended product",
                "Improve air circulation",
                "Avoid overhead watering",
                "Monitor daily for improvement",
            ],
            "product_guidance": [
                {"product_id": p["product_id"], "name": p["name"],
                 "how_to_use": p["usage"], "frequency": "Every 7-10 days",
                 "caution": "Follow label instructions"}
                for p in products
            ],
            "prevention": [
                "Rotate crops annually",
                "Use certified disease-free seeds",
                "Monitor regularly for early symptoms",
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  RAG ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class DiseaseRAG:

    def __init__(self, index_path: str = INDEX_PATH):
        # ── TF-IDF index (Layer 2 fallback) ──────────────────────────────────
        with open(index_path, "rb") as f:
            idx = pickle.load(f)
        self.vectorizer = idx["vectorizer"]
        self.matrix     = idx["matrix"]
        self.metas      = idx["metas"]
        self.id_to_meta = {m["product_id"]: m for m in self.metas}
        print(f"RAG ready — {len(self.metas)} products in TF-IDF index")

    # ── Layer 1: Database lookup ─────────────────────────────────────────────

    def _db_lookup(self, disease: str, max_products: int) -> list[dict]:
        """
        Query the disease_products join table.
        Returns up to max_products product dicts, or [] if disease not found.
        """
        canonical = _normalise_disease(disease)
        db = _get_db()
        try:
            rows = (
                db.query(Product)
                .join(DiseaseProduct, DiseaseProduct.product_id == Product.product_id)
                .join(Disease, Disease.id == DiseaseProduct.disease_id)
                .filter(Disease.name == canonical)
                .limit(max_products)
                .all()
            )
            return [self._product_row_to_dict(p) for p in rows]
        finally:
            db.close()

    def _product_row_to_dict(self, p: Product) -> dict:
        """Convert a SQLAlchemy Product row to the standard product dict."""
        meta = self.id_to_meta.get(p.product_id, {})
        return {
            "product_id":   p.product_id,
            "name":         p.name,
            "product_type": p.product_type or "",
            "ingredients":  p.ingredients or "",
            "usage":        self._format_usage_str(p.usage or "", p.dilution or ""),
            "raw_usage":    p.usage or "",
            "dilution":     p.dilution or "",
            "spec":         p.spec or "",
            "match_score":  1.0,     # DB match = highest confidence
            "source":       "db",
        }

    # ── Layer 2: TF-IDF vector search ────────────────────────────────────────

    def _build_query(self, crop, disease):
        return f"{crop} {disease} treatment"

    def _rerank(self, meta: dict, cosine: float, crop: str, disease: str) -> float:
        score = cosine
        crops_txt = (meta.get("crops", "") or "").lower()
        usage_txt = (meta.get("usage", "") or "").lower()
        if crop.lower()    in crops_txt: score += 0.25
        if disease.lower() in crops_txt: score += 0.20
        if disease.lower() in usage_txt: score += 0.15
        if "fungicide"     in usage_txt: score += 0.10
        if meta.get("product_type", "").lower() == "pesticide": score += 0.05
        return round(score, 4)

    def _tfidf_search(self, crop: str, disease: str, top_k: int = TOP_K) -> list[dict]:
        qvec    = self.vectorizer.transform([self._build_query(crop, disease)])
        cosines = cosine_similarity(qvec, self.matrix)[0]
        top_idx = np.argsort(cosines)[::-1][:top_k]
        results = [
            {"score": self._rerank(self.metas[i], float(cosines[i]), crop, disease),
             **self.metas[i]}
            for i in top_idx
        ]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _format_usage_str(self, usage: str, dilution: str) -> str:
        if usage and len(usage) > 10:
            sentence = re.split(r"[.;|\n]", usage)[0].strip()
            return sentence[:200] if sentence else usage[:200]
        return dilution or "Follow label instructions"

    def _format_usage(self, meta: dict) -> str:
        return self._format_usage_str(
            meta.get("usage", "") or "",
            meta.get("dilution", "") or "",
        )

    def _to_product_dict(self, meta: dict, score: float = 0.0) -> dict:
        return {
            "product_id":   meta["product_id"],
            "name":         meta["name"],
            "product_type": meta["product_type"],
            "ingredients":  meta.get("ingredients", ""),
            "usage":        self._format_usage(meta),
            "raw_usage":    meta.get("usage", ""),
            "dilution":     meta.get("dilution", ""),
            "spec":         meta.get("spec", ""),
            "match_score":  round(score, 4),
            "price":        meta.get("price"),
            "source":       "rag",
        }

    def get_products(self, crop: str, disease: str, max_products: int = MAX_PRODUCTS) -> list[dict]:
        """
        Two-layer product lookup:
          Layer 1 — DB join on disease_products (exact, curated)
          Layer 2 — TF-IDF fallback (if DB returns nothing)
        """
        # ── Layer 1: DB ───────────────────────────────────────────────────────
        db_products = self._db_lookup(disease, max_products)

        if db_products:
            return db_products   # DB hit — done, skip TF-IDF entirely

        # ── Layer 2: TF-IDF (disease not in mapping table yet) ────────────────
        products  = []
        used_ids  = set()
        for c in self._tfidf_search(crop, disease):
            if c["product_id"] not in used_ids:
                products.append(self._to_product_dict(c, c["score"]))
                used_ids.add(c["product_id"])
            if len(products) >= max_products:
                break
        return products

    # ── Response assembler ───────────────────────────────────────────────────

    def _build_response(
        self,
        crop: str,
        disease: str,
        products: list[dict],
        llm_result: dict,
        pathogen_fact: str,
    ) -> dict:
        guid_by_id = {g["product_id"]: g for g in llm_result.get("product_guidance", [])}
        recommended = []
        for p in products:
            g = guid_by_id.get(p["product_id"], {})
            recommended.append({
                "product_id":   p["product_id"],
                "name":         p["name"],
                "product_type": p["product_type"],
                "ingredients":  p["ingredients"],
                "spec":         p["spec"],
                "how_to_use":   g.get("how_to_use"),
                "frequency":    g.get("frequency", "Every 7-10 days"),
                "caution":      g.get("caution", "Follow label instructions"),
                "match_score":  p["match_score"],
                "source":       p.get("source", "rag"),
                "price":        p.get("price"),
            })
        return {
            "crop":                 crop,
            "disease":              disease,
            "status":               "diseased",
            "pathogen":             llm_result.get("pathogen", pathogen_fact),
            "summary":              llm_result.get("summary", ""),
            "severity":             llm_result.get("severity", "Medium"),
            "treatment":            llm_result.get("treatment", []),
            "recommended_products": recommended,
            "prevention":           llm_result.get("prevention", []),
        }

    # ── Public entry points ──────────────────────────────────────────────────

    def query_by_class(
        self,
        class_label: str,
        max_products: int = MAX_PRODUCTS,
        use_llm: bool = True,
    ) -> dict:
        """
        Primary entry point — feed the raw vision model class label.
        e.g. "Tomato_Early_blight", "Pepper__bell___Bacterial_spot"
        """
        info = CLASS_MAP.get(class_label)
        if info is None:
            return {"error": f"Unknown class label: '{class_label}'",
                    "known_classes": list(CLASS_MAP.keys())}

        crop = info["crop"]
        if info["healthy"]:
            return _healthy_response(crop)

        disease       = info["disease"]
        key           = disease.lower()
        pathogen_fact = PATHOGEN_FACTS.get(key, f"{disease} — pathogen details unavailable")
        products      = self.get_products(crop, disease, max_products)

        if use_llm:
            llm_result = generate_treatment(crop, disease, pathogen_fact, products)
        else:
            llm_result = {
                "pathogen":  pathogen_fact,
                "summary":   f"{disease} detected on {crop}.",
                "severity":  "Medium",
                "treatment": ["Remove infected leaves", "Apply treatment", "Improve drainage"],
                "product_guidance": [
                    {"product_id": p["product_id"], "name": p["name"],
                     "how_to_use": p["usage"], "frequency": "Every 7-10 days",
                     "caution": "Follow label"}
                    for p in products
                ],
                "prevention": ["Rotate crops", "Use disease-free seeds", "Monitor regularly"],
            }
        return self._build_response(crop, disease, products, llm_result, pathogen_fact)

    def query(
        self,
        crop: str,
        disease: str,
        max_products: int = MAX_PRODUCTS,
        use_llm: bool = True,
        vision_context: dict | None = None,
    ) -> dict:
        """
        Free-text entry point — for diseases not in CLASS_MAP
        (e.g. "apple scab", "powdery mildew", any GPT vision output).

        vision_context — optional GPT vision symptoms dict to enrich the prompt.
        """
        # Try exact CLASS_MAP match first
        for label, info in CLASS_MAP.items():
            if (info["crop"].lower() == crop.lower()
                    and (info.get("disease") or "").lower() == disease.lower()):
                return self.query_by_class(label, max_products, use_llm)

        key           = disease.lower()
        pathogen_fact = PATHOGEN_FACTS.get(key, f"{disease} — pathogen details unavailable")
        products      = self.get_products(crop, disease, max_products)

        if use_llm:
            llm_result = generate_treatment(
                crop, disease, pathogen_fact, products,
                vision_context=vision_context,
            )
        else:
            llm_result = {
                "pathogen":        pathogen_fact,
                "summary":         "",
                "severity":        "Medium",
                "treatment":       [],
                "product_guidance": [],
                "prevention":      [],
            }
        return self._build_response(crop, disease, products, llm_result, pathogen_fact)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    rag     = DiseaseRAG()
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    print(f"OpenAI key : {'found ✓' if has_key else 'NOT SET — offline fallback'}\n")

    tests = [
        # Known PlantVillage classes
        ("class", "Tomato_Early_blight"),
        ("class", "Tomato_Spider_mites_Two_spotted_spider_mite"),
        ("class", "Potato___Late_blight"),
        ("class", "Tomato_healthy"),
        # Free-text diseases from the CSV mapping
        ("free",  ("Tomato",  "Downy Mildew")),
        ("free",  ("Pepper",  "Aphids")),
        ("free",  ("Apple",   "Scab")),
        ("free",  ("Wheat",   "Rust")),
    ]

    if "--all" in sys.argv:
        tests += [("class", lbl) for lbl in CLASS_MAP.keys()]

    for kind, arg in tests:
        print("\n" + "=" * 65)
        if kind == "class":
            print(f"CLASS: {arg}")
            result = rag.query_by_class(arg, use_llm=has_key)
        else:
            crop, disease = arg
            print(f"FREE-TEXT: {crop} / {disease}")
            result = rag.query(crop=crop, disease=disease, use_llm=has_key)
        print(f"Source: {result.get('recommended_products', [{}])[0].get('source', 'n/a') if result.get('recommended_products') else 'none'}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
