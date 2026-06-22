"""
database.py  —  AgroMind PostgreSQL models
==========================================

Tables:
  users            — registered accounts
  diagnoses        — every scan (full result saved as JSON columns)
  products         — 114 products from Excel  (seeded by seed_db.py)
  diseases         — 20 disease names         (seeded by seed_db.py)
  disease_products — 201 disease→product rows (seeded by seed_db.py)
                     THIS is the join table that replaces the
                     DISEASE_PRODUCTS dict that was hard-coded in query.py
  cart_items       — products currently sitting in a user's cart
  orders           — one row per completed checkout
  order_items      — product lines inside an order (price snapshotted)
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    Float, Integer, create_engine, Column, String, Text,
    DateTime, ForeignKey, Boolean, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/agromind"
)

engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base         = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(String,  primary_key=True)
    email            = Column(String,  unique=True, nullable=False, index=True)
    hashed_password  = Column(String,  nullable=False)
    full_name        = Column(String,  nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    is_active        = Column(Boolean, default=True)

    diagnoses        = relationship("Diagnosis", back_populates="user",
                                    cascade="all, delete-orphan")
    cart_items       = relationship("CartItem", back_populates="user",
                                    cascade="all, delete-orphan")
    orders           = relationship("Order", back_populates="user",
                                    cascade="all, delete-orphan")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id           = Column(String,  primary_key=True)
    user_id      = Column(String,  ForeignKey("users.id"), nullable=True, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)

    # GPT vision output
    crop         = Column(String, nullable=True)
    disease_name = Column(String, nullable=True)
    growth_stage = Column(String, nullable=True)
    confidence   = Column(String, nullable=True)
    disease_type = Column(String, nullable=True)
    spread_rate  = Column(String, nullable=True)
    severity     = Column(String, nullable=True)
    symptoms     = Column(JSON,   nullable=True)
    explanation  = Column(Text,   nullable=True)

    # RAG + GPT treatment output
    status       = Column(String, nullable=True)
    pathogen     = Column(String, nullable=True)
    summary      = Column(Text,   nullable=True)
    treatment    = Column(JSON,   nullable=True)
    prevention   = Column(JSON,   nullable=True)
    recommended_products = Column(JSON, nullable=True)

    user         = relationship("User", back_populates="diagnoses")


class Product(Base):
    """114 products from the Excel catalog."""
    __tablename__ = "products"

    product_id   = Column(String, primary_key=True)   # e.g. PN0002
    name         = Column(String, nullable=False)
    product_type = Column(String, nullable=True)
    crops        = Column(Text,   nullable=True)
    ingredients  = Column(Text,   nullable=True)
    usage        = Column(Text,   nullable=True)
    dilution     = Column(String, nullable=True)
    spec         = Column(String, nullable=True)
    price        = Column(Float, nullable=True) 

    disease_links = relationship("DiseaseProduct", back_populates="product")


class Disease(Base):
    """
    20 unique disease / pest names from the mapping CSV.
    One row per disease — normalised so you can add metadata later
    (e.g. pathogen, severity_default, description).
    """
    __tablename__ = "diseases"

    id           = Column(String, primary_key=True)   # slug, e.g. "downy-mildew"
    name         = Column(String, unique=True, nullable=False)  # "downy mildew"
    pathogen     = Column(String, nullable=True)
    description  = Column(Text,   nullable=True)

    product_links = relationship("DiseaseProduct", back_populates="disease")


class DiseaseProduct(Base):
    """
    Join table — 201 rows from disease_product_map.csv.
    Answers: "which products treat this disease?"

    This replaces the hard-coded DISEASE_PRODUCTS dictionary
    that was in query.py.
    """
    __tablename__ = "disease_products"

    disease_id   = Column(String, ForeignKey("diseases.id"),     primary_key=True)
    product_id   = Column(String, ForeignKey("products.product_id"), primary_key=True)

    # Composite PK prevents duplicate rows on re-seed
    __table_args__ = (
        UniqueConstraint("disease_id", "product_id", name="uq_disease_product"),
    )

    disease  = relationship("Disease", back_populates="product_links")
    product  = relationship("Product", back_populates="disease_links")

class CartItem(Base):
    """
    A product sitting in a user's cart, not yet purchased.
    One row per (user, product) — adding the same product again
    just bumps the quantity instead of creating a duplicate row.
    """
    __tablename__ = "cart_items"
 
    id           = Column(String,  primary_key=True)   # uuid4
    user_id      = Column(String,  ForeignKey("users.id"), nullable=False, index=True)
    product_id   = Column(String,  ForeignKey("products.product_id"), nullable=False, index=True)
    quantity     = Column(Integer, nullable=False, default=1)
    added_at     = Column(DateTime, default=datetime.utcnow)
 
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_cart"),
    )
 
    user     = relationship("User", back_populates="cart_items")
    product  = relationship("Product")
 
 
class Order(Base):
    """
    A completed purchase — created at checkout from the user's cart.
    Line items live in OrderItem.
    """
    __tablename__ = "orders"
 
    id           = Column(String,  primary_key=True)   # uuid4
    user_id      = Column(String,  ForeignKey("users.id"), nullable=False, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)
    status       = Column(String,  nullable=False, default="completed")  # completed/cancelled
    total_price  = Column(Float,   nullable=True)
 
    user   = relationship("User", back_populates="orders")
    items  = relationship("OrderItem", back_populates="order",
                          cascade="all, delete-orphan")
 
 
class OrderItem(Base):
    """
    One product line inside an Order.
    price_at_purchase snapshots Product.price so later price
    changes don't rewrite historical order totals.
    """
    __tablename__ = "order_items"
 
    id                 = Column(String,  primary_key=True)   # uuid4
    order_id           = Column(String,  ForeignKey("orders.id"), nullable=False, index=True)
    product_id         = Column(String,  ForeignKey("products.product_id"), nullable=False)
    quantity           = Column(Integer, nullable=False, default=1)
    price_at_purchase  = Column(Float,   nullable=True)
 
    order    = relationship("Order", back_populates="items")
    product  = relationship("Product")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency — yields a session, closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables (safe — skips existing)."""
    Base.metadata.create_all(bind=engine)
