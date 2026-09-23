import os, json, hashlib
import stripe
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, ForeignKey, select, func, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

BASE = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE/'lpfb.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-IN-RENDER")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "true").lower() in ("1","true","yes","on")
BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
BOOTSTRAP_ADMIN_NAME = os.getenv("BOOTSTRAP_ADMIN_NAME", "Administrateur Le Panier Frais Bio")
PRODUCTION_STRICT = os.getenv("PRODUCTION_STRICT", "true").lower() in ("1","true","yes","on")
SITE_URL = os.getenv("SITE_URL", "").rstrip("/")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "")
TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
RELEASE_CHANNEL = os.getenv("RELEASE_CHANNEL", "candidate")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "eur").strip().lower() or "eur"
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "").strip()
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "").strip()
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
DEMO_ADMIN_EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "")
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "")
DEMO_PRO_EMAIL = os.getenv("DEMO_PRO_EMAIL", "")
DEMO_PRO_PASSWORD = os.getenv("DEMO_PRO_PASSWORD", "")
DEMO_B2C_EMAIL = os.getenv("DEMO_B2C_EMAIL", "")
DEMO_B2C_PASSWORD = os.getenv("DEMO_B2C_PASSWORD", "")

AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "false" if ENVIRONMENT=="production" else "true").lower() in ("1","true","yes","on")


if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    full_name: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(50),default="ADMIN")
    active: Mapped[int]=mapped_column(Integer,default=1)
    created_at: Mapped[str]=mapped_column(String(50))

class Client(Base):
    __tablename__="clients"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_type: Mapped[str]=mapped_column(String(30))
    name: Mapped[str]=mapped_column(String(255))
    email: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    active: Mapped[int]=mapped_column(Integer,default=1)

class Product(Base):
    __tablename__="products"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    reference: Mapped[str]=mapped_column(String(80),unique=True,index=True)
    name: Mapped[str]=mapped_column(String(255))
    family: Mapped[str]=mapped_column(String(80),default="Fruits & légumes")
    unit: Mapped[str]=mapped_column(String(30),default="kg")
    price_ht: Mapped[float]=mapped_column(Float,default=0)
    active: Mapped[int]=mapped_column(Integer,default=1)

class ProductAvailability(Base):
    __tablename__="product_availability"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),unique=True)
    order_mode: Mapped[str]=mapped_column(String(40),default="SUR_COMMANDE")
    supplier_lead_days: Mapped[int]=mapped_column(Integer,default=2)
    allow_order: Mapped[int]=mapped_column(Integer,default=1)
    notes: Mapped[str]=mapped_column(String(500),default="")
    product: Mapped["Product"]=relationship()

class ProcurementRequest(Base):
    __tablename__="procurement_requests"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    requested_qty: Mapped[float]=mapped_column(Float,default=0)
    source_type: Mapped[str]=mapped_column(String(30),default="CLIENT")
    source_order_id: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    client_id: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    status: Mapped[str]=mapped_column(String(40),default="A_APPROVISIONNER")
    note: Mapped[str]=mapped_column(String(1000),default="")
    created_at: Mapped[str]=mapped_column(String(50))
    product: Mapped["Product"]=relationship()

class ProcurementPurchaseLink(Base):
    __tablename__="procurement_purchase_links"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    procurement_request_id: Mapped[int]=mapped_column(ForeignKey("procurement_requests.id"))
    purchase_order_line_id: Mapped[int]=mapped_column(ForeignKey("purchase_order_lines.id"))
    allocated_qty: Mapped[float]=mapped_column(Float,default=0)
    fulfilled_qty: Mapped[float]=mapped_column(Float,default=0)
    procurement_request: Mapped["ProcurementRequest"]=relationship()
    purchase_order_line: Mapped["PurchaseOrderLine"]=relationship()

class GeneralSourcingRequest(Base):
    __tablename__="general_sourcing_requests"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    requested_name: Mapped[str]=mapped_column(String(255))
    category: Mapped[str]=mapped_column(String(100),default="Fruits & légumes")
    quantity_text: Mapped[str]=mapped_column(String(100),default="")
    customer_email: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    note: Mapped[str]=mapped_column(String(1000),default="")
    status: Mapped[str]=mapped_column(String(40),default="A_TRAITER")
    created_at: Mapped[str]=mapped_column(String(50))

class ProductSourcingRequest(Base):
    __tablename__="product_sourcing_requests"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    customer_email: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    quantity: Mapped[float]=mapped_column(Float,default=1)
    note: Mapped[str]=mapped_column(String(1000),default="")
    status: Mapped[str]=mapped_column(String(40),default="A_TRAITER")
    created_at: Mapped[str]=mapped_column(String(50))
    product: Mapped["Product"]=relationship()

class ProductCostProfile(Base):
    __tablename__="product_cost_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),unique=True)
    purchase_cost_ht: Mapped[float]=mapped_column(Float,default=0)
    packaging_cost_ht: Mapped[float]=mapped_column(Float,default=0)
    labor_cost_ht: Mapped[float]=mapped_column(Float,default=0)
    other_cost_ht: Mapped[float]=mapped_column(Float,default=0)
    target_margin_pct: Mapped[float]=mapped_column(Float,default=35)
    product: Mapped["Product"]=relationship()

class ProductPriceHistory(Base):
    __tablename__="product_price_history"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    price_ht: Mapped[float]=mapped_column(Float)
    reason: Mapped[str]=mapped_column(String(500),default="")
    changed_at: Mapped[str]=mapped_column(String(50))
    changed_by: Mapped[str]=mapped_column(String(255),default="")
    product: Mapped["Product"]=relationship()

class ProductMedia(Base):
    __tablename__="product_media"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),unique=True)
    image_url: Mapped[str]=mapped_column(String(1000))
    alt_text: Mapped[str]=mapped_column(String(255),default="")
    badge: Mapped[str]=mapped_column(String(100),default="Le Panier Frais Bio")
    active: Mapped[int]=mapped_column(Integer,default=1)
    product: Mapped["Product"]=relationship()

class MarketingVisual(Base):
    __tablename__="marketing_visuals"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    placement: Mapped[str]=mapped_column(String(80))
    title: Mapped[str]=mapped_column(String(255))
    subtitle: Mapped[str]=mapped_column(String(500),default="")
    image_url: Mapped[str]=mapped_column(String(1000))
    target_filter: Mapped[str]=mapped_column(String(255),default="")
    active: Mapped[int]=mapped_column(Integer,default=1)
    sort_order: Mapped[int]=mapped_column(Integer,default=0)

class ProductCut(Base):
    __tablename__="product_cuts"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    cut_name: Mapped[str]=mapped_column(String(100))
    yield_rate: Mapped[float]=mapped_column(Float,default=1.0)
    extra_price_ht: Mapped[float]=mapped_column(Float,default=0.0)

class Lot(Base):
    __tablename__="lots"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    internal_lot: Mapped[str]=mapped_column(String(100),unique=True,index=True)
    supplier_lot: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    qty_received: Mapped[float]=mapped_column(Float)
    qty_reserved: Mapped[float]=mapped_column(Float,default=0)
    qty_consumed: Mapped[float]=mapped_column(Float,default=0)
    expiry_date: Mapped[Optional[str]]=mapped_column(String(20),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="LIBERE")
    product: Mapped["Product"]=relationship()

class LotStageInfo(Base):
    __tablename__="lot_stage_info"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    lot_id: Mapped[int]=mapped_column(ForeignKey("lots.id"),unique=True,index=True)
    stage: Mapped[str]=mapped_column(String(20),default="RAW")
    source: Mapped[str]=mapped_column(String(80),default="LEGACY")
    updated_at: Mapped[str]=mapped_column(String(50))
    lot: Mapped["Lot"]=relationship()

class Order(Base):
    __tablename__="orders"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"))
    status: Mapped[str]=mapped_column(String(30),default="CONFIRMEE")
    delivery_mode: Mapped[str]=mapped_column(String(50),default="LIVRAISON")
    created_at: Mapped[str]=mapped_column(String(50))
    client: Mapped["Client"]=relationship()

class OrderLine(Base):
    __tablename__="order_lines"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float]=mapped_column(Float)
    unit_price_ht: Mapped[float]=mapped_column(Float,default=0)
    product: Mapped["Product"]=relationship()

class OrderOption(Base):
    __tablename__="order_options"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"),unique=True)
    cut_name: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    note: Mapped[Optional[str]]=mapped_column(String(500),nullable=True)

class Reservation(Base):
    __tablename__="reservations"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    lot_id: Mapped[int]=mapped_column(ForeignKey("lots.id"))
    quantity: Mapped[float]=mapped_column(Float)
    status: Mapped[str]=mapped_column(String(30),default="ACTIVE")

class ProductionJob(Base):
    __tablename__="production_jobs"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity_needed: Mapped[float]=mapped_column(Float)
    status: Mapped[str]=mapped_column(String(30),default="A_PLANIFIER")
    source_order_id: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    created_at: Mapped[str]=mapped_column(String(50))
    product: Mapped["Product"]=relationship()

class ProductionBatch(Base):
    __tablename__="production_batches"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    job_id: Mapped[int]=mapped_column(ForeignKey("production_jobs.id"),unique=True)
    output_lot_id: Mapped[Optional[int]]=mapped_column(ForeignKey("lots.id"),nullable=True)
    cut_name: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    packaging: Mapped[str]=mapped_column(String(100),default="À définir")
    actual_input_qty: Mapped[float]=mapped_column(Float,default=0)
    actual_output_qty: Mapped[float]=mapped_column(Float,default=0)
    temperature_c: Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    quality_status: Mapped[str]=mapped_column(String(30),default="A_VALIDER")
    operator_notes: Mapped[str]=mapped_column(String(1000),default="")
    completed_at: Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    job: Mapped["ProductionJob"]=relationship()
    output_lot: Mapped[Optional["Lot"]]=relationship(foreign_keys=[output_lot_id])

class ProductionConsumption(Base):
    __tablename__="production_consumptions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    batch_id: Mapped[int]=mapped_column(ForeignKey("production_batches.id"))
    source_lot_id: Mapped[int]=mapped_column(ForeignKey("lots.id"))
    quantity: Mapped[float]=mapped_column(Float)
    source_lot: Mapped["Lot"]=relationship()

class Delivery(Base):
    __tablename__="deliveries"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    status: Mapped[str]=mapped_column(String(30),default="A_PREPARER")
    slot: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)

class Payment(Base):
    __tablename__="payments"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"),unique=True)
    status: Mapped[str]=mapped_column(String(30),default="A_PAYER")
    method: Mapped[str]=mapped_column(String(50),default="SUR_PLACE")
    amount: Mapped[float]=mapped_column(Float,default=0)
    reference: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)

class Invoice(Base):
    __tablename__="invoices"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    status: Mapped[str]=mapped_column(String(30),default="BROUILLON")
    amount_ht: Mapped[float]=mapped_column(Float,default=0)

class ProductTaxProfile(Base):
    __tablename__="product_tax_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),unique=True)
    tax_rate_pct: Mapped[float]=mapped_column(Float,default=0)
    tax_label: Mapped[str]=mapped_column(String(100),default="À configurer")
    product: Mapped["Product"]=relationship()

class InvoiceFiscalSummary(Base):
    __tablename__="invoice_fiscal_summaries"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    invoice_id: Mapped[int]=mapped_column(ForeignKey("invoices.id"),unique=True)
    invoice_number: Mapped[Optional[str]]=mapped_column(String(80),unique=True,nullable=True)
    amount_ht: Mapped[float]=mapped_column(Float,default=0)
    amount_tax: Mapped[float]=mapped_column(Float,default=0)
    amount_ttc: Mapped[float]=mapped_column(Float,default=0)
    issued_at: Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    due_date: Mapped[Optional[str]]=mapped_column(String(20),nullable=True)

class InvoiceTaxLine(Base):
    __tablename__="invoice_tax_lines"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    invoice_id: Mapped[int]=mapped_column(ForeignKey("invoices.id"))
    order_line_id: Mapped[int]=mapped_column(ForeignKey("order_lines.id"))
    product_name: Mapped[str]=mapped_column(String(255))
    quantity: Mapped[float]=mapped_column(Float)
    unit_price_ht: Mapped[float]=mapped_column(Float)
    tax_rate_pct: Mapped[float]=mapped_column(Float)
    amount_ht: Mapped[float]=mapped_column(Float)
    amount_tax: Mapped[float]=mapped_column(Float)
    amount_ttc: Mapped[float]=mapped_column(Float)

class CreditNote(Base):
    __tablename__="credit_notes"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    invoice_id: Mapped[int]=mapped_column(ForeignKey("invoices.id"))
    credit_number: Mapped[str]=mapped_column(String(80),unique=True)
    reason: Mapped[str]=mapped_column(String(500))
    amount_ht: Mapped[float]=mapped_column(Float,default=0)
    amount_tax: Mapped[float]=mapped_column(Float,default=0)
    amount_ttc: Mapped[float]=mapped_column(Float,default=0)
    created_at: Mapped[str]=mapped_column(String(50))
    status: Mapped[str]=mapped_column(String(30),default="BROUILLON")

class Supplier(Base):
    __tablename__="suppliers"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str]=mapped_column(String(255),unique=True)
    city: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    specialty: Mapped[Optional[str]]=mapped_column(String(500),nullable=True)
    active: Mapped[int]=mapped_column(Integer,default=1)

class SupplierProduct(Base):
    __tablename__="supplier_products"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    supplier_id: Mapped[int]=mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    supplier_reference: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    last_price_ht: Mapped[float]=mapped_column(Float,default=0)
    min_order_qty: Mapped[float]=mapped_column(Float,default=0)
    lead_time_days: Mapped[int]=mapped_column(Integer,default=0)
    active: Mapped[int]=mapped_column(Integer,default=1)
    supplier: Mapped["Supplier"]=relationship()
    product: Mapped["Product"]=relationship()

class PurchaseOrder(Base):
    __tablename__="purchase_orders"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    supplier_id: Mapped[int]=mapped_column(ForeignKey("suppliers.id"))
    status: Mapped[str]=mapped_column(String(30),default="BROUILLON")
    expected_date: Mapped[Optional[str]]=mapped_column(String(20),nullable=True)
    note: Mapped[str]=mapped_column(String(1000),default="")
    created_at: Mapped[str]=mapped_column(String(50))
    supplier: Mapped["Supplier"]=relationship()

class PurchaseOrderLine(Base):
    __tablename__="purchase_order_lines"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    purchase_order_id: Mapped[int]=mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float]=mapped_column(Float)
    unit_price_ht: Mapped[float]=mapped_column(Float,default=0)
    received_qty: Mapped[float]=mapped_column(Float,default=0)
    product: Mapped["Product"]=relationship()

class PurchaseReceipt(Base):
    __tablename__="purchase_receipts"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    purchase_order_id: Mapped[int]=mapped_column(ForeignKey("purchase_orders.id"))
    received_at: Mapped[str]=mapped_column(String(50))
    note: Mapped[str]=mapped_column(String(1000),default="")

class PurchaseReceiptLine(Base):
    __tablename__="purchase_receipt_lines"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    receipt_id: Mapped[int]=mapped_column(ForeignKey("purchase_receipts.id"))
    purchase_order_line_id: Mapped[int]=mapped_column(ForeignKey("purchase_order_lines.id"))
    received_qty: Mapped[float]=mapped_column(Float)
    internal_lot: Mapped[str]=mapped_column(String(100))
    supplier_lot: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    expiry_date: Mapped[Optional[str]]=mapped_column(String(20),nullable=True)
    lot_status: Mapped[str]=mapped_column(String(30),default="BLOQUE")

class Equipment(Base):
    __tablename__="equipment"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str]=mapped_column(String(255))
    budget_low: Mapped[float]=mapped_column(Float,default=0)
    budget_high: Mapped[float]=mapped_column(Float,default=0)
    priority: Mapped[str]=mapped_column(String(40),default="INDISPENSABLE")
    status: Mapped[str]=mapped_column(String(40),default="A_ACHETER")

class PreparationProfile(Base):
    __tablename__="preparation_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    cut_name: Mapped[str]=mapped_column(String(100),default="Standard")
    portion_g: Mapped[float]=mapped_column(Float,default=100)
    yield_rate: Mapped[float]=mapped_column(Float,default=1.0)
    b2c_formats: Mapped[str]=mapped_column(String(255),default="250 g, 500 g, 750 g, 1 kg")
    pro_formats: Mapped[str]=mapped_column(String(255),default="1 kg, 2.5 kg, 5 kg, 10 kg")
    uses: Mapped[str]=mapped_column(String(1000),default="")
    product: Mapped["Product"]=relationship()

class Recipe(Base):
    __tablename__="recipes"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str]=mapped_column(String(255),unique=True)
    category: Mapped[str]=mapped_column(String(80),default="Recette")
    default_servings: Mapped[int]=mapped_column(Integer,default=2)
    description: Mapped[str]=mapped_column(String(1000),default="")
    active: Mapped[int]=mapped_column(Integer,default=1)

class RecipeIngredient(Base):
    __tablename__="recipe_ingredients"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    recipe_id: Mapped[int]=mapped_column(ForeignKey("recipes.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    grams_per_serving: Mapped[float]=mapped_column(Float,default=100)
    cut_name: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    product: Mapped["Product"]=relationship()

class PackagingFormat(Base):
    __tablename__="packaging_formats"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    segment: Mapped[str]=mapped_column(String(20),default="B2C")
    label: Mapped[str]=mapped_column(String(80))
    quantity_g: Mapped[float]=mapped_column(Float,default=500)
    recommended_use: Mapped[str]=mapped_column(String(500),default="")
    active: Mapped[int]=mapped_column(Integer,default=1)

class B2CUserLink(Base):
    __tablename__="b2c_user_links"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"),unique=True)
    client: Mapped["Client"]=relationship()

class B2CProfile(Base):
    __tablename__="b2c_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"),unique=True)
    household_size: Mapped[int]=mapped_column(Integer,default=2)
    weekly_budget: Mapped[float]=mapped_column(Float,default=45.0)
    goals: Mapped[str]=mapped_column(String(500),default="Manger équilibré")
    disliked_foods: Mapped[str]=mapped_column(String(1000),default="")
    declared_allergies: Mapped[str]=mapped_column(String(1000),default="")
    favorite_pickup_slot: Mapped[str]=mapped_column(String(100),default="18:00 - 19:00")
    preferred_mode: Mapped[str]=mapped_column(String(50),default="CLICK_COLLECT")
    loyalty_points: Mapped[int]=mapped_column(Integer,default=0)
    client: Mapped["Client"]=relationship()

class B2CFavorite(Base):
    __tablename__="b2c_favorites"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    product: Mapped["Product"]=relationship()

class B2CSubscription(Base):
    __tablename__="b2c_subscriptions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"))
    name: Mapped[str]=mapped_column(String(255),default="Panier semaine")
    frequency: Mapped[str]=mapped_column(String(50),default="HEBDOMADAIRE")
    budget: Mapped[float]=mapped_column(Float,default=35.0)
    pickup_day: Mapped[str]=mapped_column(String(50),default="Vendredi")
    active: Mapped[int]=mapped_column(Integer,default=1)

class ProUserLink(Base):
    __tablename__="pro_user_links"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"),unique=True)
    client: Mapped["Client"]=relationship()

class ProOrderTemplate(Base):
    __tablename__="pro_order_templates"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"))
    name: Mapped[str]=mapped_column(String(255))
    delivery_mode: Mapped[str]=mapped_column(String(50),default="LIVRAISON")
    active: Mapped[int]=mapped_column(Integer,default=1)
    client: Mapped["Client"]=relationship()

class ProOrderTemplateLine(Base):
    __tablename__="pro_order_template_lines"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    template_id: Mapped[int]=mapped_column(ForeignKey("pro_order_templates.id"))
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity_kg: Mapped[float]=mapped_column(Float,default=1)
    cut_name: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    pack_size_kg: Mapped[float]=mapped_column(Float,default=2.5)
    product: Mapped["Product"]=relationship()

class ProOrderLineDetail(Base):
    __tablename__="pro_order_line_details"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_line_id: Mapped[int]=mapped_column(ForeignKey("order_lines.id"),unique=True)
    cut_name: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)
    pack_size_kg: Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    note: Mapped[Optional[str]]=mapped_column(String(500),nullable=True)

class ProRestaurantProfile(Base):
    __tablename__="pro_restaurant_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    client_id: Mapped[int]=mapped_column(ForeignKey("clients.id"),unique=True)
    covers_lunch: Mapped[int]=mapped_column(Integer,default=30)
    covers_dinner: Mapped[int]=mapped_column(Integer,default=40)
    delivery_days: Mapped[str]=mapped_column(String(255),default="Mardi, Vendredi")
    default_pack_kg: Mapped[float]=mapped_column(Float,default=2.5)
    prep_hour_cost: Mapped[float]=mapped_column(Float,default=20.0)
    prep_minutes_per_kg: Mapped[float]=mapped_column(Float,default=12.0)
    notes: Mapped[str]=mapped_column(String(1000),default="")
    client: Mapped["Client"]=relationship()

class AppSetting(Base):
    __tablename__="app_settings"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    key: Mapped[str]=mapped_column(String(100),unique=True)
    value: Mapped[str]=mapped_column(String(1000))

class AuditLog(Base):
    __tablename__="audit_log"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    created_at: Mapped[str]=mapped_column(String(50))
    event_type: Mapped[str]=mapped_column(String(100))
    details: Mapped[str]=mapped_column(String(1000))

class B2CCheckoutLineIn(BaseModel):
    product_id:int
    quantity:float=Field(gt=0)
    cut_name:Optional[str]=None

class B2CCheckoutIn(BaseModel):
    delivery_mode:str=Field(default="CLICK_COLLECT",max_length=50)
    slot:str=Field(default="18:00 - 19:00",max_length=100)
    note:str=Field(default="",max_length=500)
    payment_method:str=Field(default="SUR_PLACE",max_length=50)
    lines:list[B2CCheckoutLineIn]

class B2CProfileIn(BaseModel):
    household_size:int=Field(default=2,ge=1,le=12)
    weekly_budget:float=Field(default=45.0,ge=0,le=2000)
    goals:str=Field(default="Manger équilibré",max_length=500)
    disliked_foods:str=Field(default="",max_length=1000)
    declared_allergies:str=Field(default="",max_length=1000)
    favorite_pickup_slot:str=Field(default="18:00 - 19:00",max_length=100)
    preferred_mode:str=Field(default="CLICK_COLLECT",max_length=50)

class B2CSubscriptionIn(BaseModel):
    name:str=Field(default="Panier semaine",max_length=255)
    frequency:str=Field(default="HEBDOMADAIRE",max_length=50)
    budget:float=Field(default=35.0,ge=0,le=2000)
    pickup_day:str=Field(default="Vendredi",max_length=50)

class ProProfileIn(BaseModel):
    covers_lunch:int=Field(ge=0,le=2000)
    covers_dinner:int=Field(ge=0,le=2000)
    delivery_days:str=Field(max_length=255)
    default_pack_kg:float=Field(gt=0,le=20)
    prep_hour_cost:float=Field(ge=0,le=200)
    prep_minutes_per_kg:float=Field(ge=0,le=120)
    notes:str=""

class ProServiceCalcIn(BaseModel):
    product_id:int
    covers:int=Field(gt=0,le=5000)
    grams_per_cover:float=Field(gt=0,le=2000)
    cut_name:Optional[str]=None
    pack_size_kg:float=Field(default=2.5,gt=0,le=20)

app=FastAPI(title="Le Panier Frais Bio API",version="1.0.0")
app.mount("/assets", StaticFiles(directory=BASE/"assets"), name="assets")
@app.middleware("http")
async def security_headers(request:Request,call_next):
    content_length=request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length)>2_000_000:
                return JSONResponse({"detail":"Requête trop volumineuse"},status_code=413)
        except ValueError:
            return JSONResponse({"detail":"Content-Length invalide"},status_code=400)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"]="same-origin"
    response.headers["Cross-Origin-Resource-Policy"]="same-site"
    response.headers["Content-Security-Policy"]=(
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "img-src 'self' data: https:; font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; form-action 'self' https://checkout.stripe.com; "
        "frame-src https://checkout.stripe.com https://js.stripe.com https://hooks.stripe.com"
    )
    if request.url.path.startswith(("/auth/","/b2c/","/pro/","/admin","/payments")):
        response.headers["Cache-Control"]="no-store"
    if ENVIRONMENT=="production":
        response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response

ALLOWED_ORIGINS_RAW=os.getenv("ALLOWED_ORIGINS","*")
ALLOWED_ORIGINS=[x.strip() for x in ALLOWED_ORIGINS_RAW.split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS or ["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
DUMMY_PASSWORD_HASH=pwd.hash("LPFB-dummy-password-not-valid")
oauth=OAuth2PasswordBearer(tokenUrl="/auth/login")
STAFF_ROLES=("ADMIN","MANAGER","VENTE","PRODUCTION","LIVRAISON","COMPTA")
MANAGED_STAFF_ROLES=("ADMIN","MANAGER","VENTE","PRODUCTION","LIVRAISON","COMPTA")

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def audit(db,event,details):
    db.add(AuditLog(created_at=datetime.now(timezone.utc).isoformat(),event_type=event,details=details))

def setting(db,key,default=""):
    row=db.scalar(select(AppSetting).where(AppSetting.key==key)); return row.value if row else default


def app_setting_bool(db:Session,key:str,default:bool=False):
    value=setting(db,key,"true" if default else "false").strip().lower()
    return value in ("1","true","yes","on")

def maintenance_state(db:Session):
    return {
        "enabled":app_setting_bool(db,"maintenance_mode",False),
        "message":setting(db,"maintenance_message","Le service est temporairement en maintenance.")
    }

def lot_stage(db:Session,lot_id:int):
    row=db.scalar(select(LotStageInfo).where(LotStageInfo.lot_id==lot_id))
    return row.stage if row else "RAW"

def set_lot_stage(db:Session,lot_id:int,stage:str,source:str):
    stage=stage.upper()
    if stage not in ("RAW","PREPARED"):
        raise ValueError("Lot stage must be RAW or PREPARED")
    row=db.scalar(select(LotStageInfo).where(LotStageInfo.lot_id==lot_id))
    if not row:
        row=LotStageInfo(lot_id=lot_id,stage=stage,source=source,updated_at=datetime.now(timezone.utc).isoformat())
        db.add(row)
    else:
        row.stage=stage; row.source=source; row.updated_at=datetime.now(timezone.utc).isoformat()
    return row

def prepared_cut_for_lot(db:Session,lot_id:int):
    batch=db.scalar(select(ProductionBatch).where(ProductionBatch.output_lot_id==lot_id))
    return batch.cut_name if batch else None

def lot_available(lot:Lot):
    return lot.qty_received-lot.qty_reserved-lot.qty_consumed

def fulfill_order_reservations(db:Session,order_id:int):
    rows=db.scalars(select(Reservation).where(Reservation.order_id==order_id,Reservation.status=="ACTIVE").order_by(Reservation.id.asc())).all()
    consumed=0.0
    for r in rows:
        lot=db.get(Lot,r.lot_id)
        if not lot:
            raise HTTPException(409,f"Lot introuvable pour réservation {r.id}")
        if r.quantity<0 or lot.qty_reserved+1e-9<r.quantity:
            raise HTTPException(409,f"Réservation incohérente sur lot {lot.internal_lot}")
        lot.qty_reserved-=r.quantity
        lot.qty_consumed+=r.quantity
        if lot_available(lot)<-1e-9:
            raise HTTPException(409,f"Stock négatif après consommation du lot {lot.internal_lot}")
        consumed+=r.quantity
        r.status="FULFILLED"
    return round(consumed,3)

def cancel_order_resources(db:Session,order:Order):
    if order.status=="ANNULEE":
        return {"released_qty":0.0,"cancelled_jobs":0,"cancelled_procurement":0,"warnings":[]}
    deliveries=db.scalars(select(Delivery).where(Delivery.order_id==order.id)).all()
    if any(d.status in ("LIVREE","RETIRÉE") for d in deliveries):
        raise HTTPException(409,"Une commande déjà livrée ou retirée ne peut pas être annulée")

    released=0.0
    for r in db.scalars(select(Reservation).where(Reservation.order_id==order.id,Reservation.status=="ACTIVE")).all():
        lot=db.get(Lot,r.lot_id)
        if not lot:
            raise HTTPException(409,f"Lot introuvable pour réservation {r.id}")
        if lot.qty_reserved+1e-9<r.quantity:
            raise HTTPException(409,f"Réservation incohérente sur lot {lot.internal_lot}")
        lot.qty_reserved-=r.quantity
        released+=r.quantity
        r.status="CANCELLED"

    cancelled_jobs=0
    for job in db.scalars(select(ProductionJob).where(ProductionJob.source_order_id==order.id)).all():
        if job.status!="TERMINE":
            job.status="ANNULE"
            cancelled_jobs+=1

    cancelled_procurement=0
    warnings=[]
    for req in db.scalars(select(ProcurementRequest).where(ProcurementRequest.source_order_id==order.id)).all():
        if req.status in ("A_APPROVISIONNER","EN_COURS"):
            req.status="ANNULE"
            cancelled_procurement+=1
        elif req.status=="COMMANDE_FOURNISSEUR":
            warnings.append(f"Approvisionnement #{req.id} déjà commandé au fournisseur : traitement manuel requis.")
    order.status="ANNULEE"
    return {"released_qty":round(released,3),"cancelled_jobs":cancelled_jobs,"cancelled_procurement":cancelled_procurement,"warnings":warnings}

def reserve_order_from_lots(db:Session,order:Order,product:Product,quantity:float,cut_name:Optional[str]=None):
    remaining=quantity
    lots=db.scalars(select(Lot).where(Lot.product_id==product.id,Lot.status=="LIBERE").order_by(Lot.expiry_date.asc(),Lot.id.asc())).all()
    candidates=[]
    for lot in lots:
        stage=lot_stage(db,lot.id)
        if cut_name:
            if stage!="PREPARED": continue
            lot_cut=prepared_cut_for_lot(db,lot.id)
            if lot_cut and lot_cut!=cut_name: continue
        else:
            if stage!="RAW": continue
        candidates.append(lot)
    for lot in candidates:
        available=max(0,lot_available(lot))
        take=min(remaining,available)
        if take>0:
            lot.qty_reserved += take
            db.add(Reservation(order_id=order.id,lot_id=lot.id,quantity=take,status="ACTIVE"))
            remaining-=take
        if remaining<=1e-9: break
    return max(0,remaining)

def reconcile_legacy_lot_stages(db:Session):
    prepared_ids=set(db.scalars(select(ProductionBatch.output_lot_id).where(ProductionBatch.output_lot_id.is_not(None))).all())
    for lot in db.scalars(select(Lot)).all():
        if db.scalar(select(LotStageInfo).where(LotStageInfo.lot_id==lot.id)):
            continue
        set_lot_stage(db,lot.id,"PREPARED" if lot.id in prepared_ids else "RAW","MIGRATION_COMPAT")

def integrity_report(db:Session):
    issues=[]
    warnings=[]
    # Stock integrity
    for lot in db.scalars(select(Lot)).all():
        available=lot_available(lot)
        stage=lot_stage(db,lot.id)
        if available < -1e-9:
            issues.append({"type":"NEGATIVE_STOCK","entity":"lot","id":lot.id,"message":f"{lot.internal_lot}: disponible {available:.3f}"})
        if lot.qty_reserved < -1e-9 or lot.qty_consumed < -1e-9:
            issues.append({"type":"INVALID_STOCK_COUNTER","entity":"lot","id":lot.id,"message":lot.internal_lot})
        if lot.qty_reserved+lot.qty_consumed > lot.qty_received+1e-9:
            issues.append({"type":"OVERALLOCATED_LOT","entity":"lot","id":lot.id,"message":lot.internal_lot})
        if stage not in ("RAW","PREPARED"):
            issues.append({"type":"INVALID_LOT_STAGE","entity":"lot","id":lot.id,"message":f"{lot.internal_lot}: {stage}"})
        if stage=="PREPARED" and not db.scalar(select(ProductionBatch).where(ProductionBatch.output_lot_id==lot.id)):
            warnings.append({"type":"PREPARED_WITHOUT_BATCH","entity":"lot","id":lot.id,"message":lot.internal_lot})
    # Reservation lifecycle integrity
    for r in db.scalars(select(Reservation)).all():
        if r.quantity<0:
            issues.append({"type":"NEGATIVE_RESERVATION","entity":"reservation","id":r.id,"message":str(r.quantity)})
        order=db.get(Order,r.order_id)
        if order and order.status in ("TERMINEE","ANNULEE") and r.status=="ACTIVE":
            issues.append({"type":"ACTIVE_RESERVATION_ON_CLOSED_ORDER","entity":"reservation","id":r.id,"message":f"order={order.id};status={order.status}"})
    for order in db.scalars(select(Order).where(Order.status=="TERMINEE")).all():
        active=db.scalar(select(func.count(Reservation.id)).where(Reservation.order_id==order.id,Reservation.status=="ACTIVE")) or 0
        if active:
            issues.append({"type":"CLOSED_ORDER_WITH_ACTIVE_RESERVATIONS","entity":"order","id":order.id,"message":f"{active} réservation(s) active(s)"})
    # Procurement linkage integrity
    for link in db.scalars(select(ProcurementPurchaseLink)).all():
        if link.fulfilled_qty > link.allocated_qty+1e-9:
            issues.append({"type":"PROCUREMENT_OVERFULFILLED","entity":"procurement_purchase_link","id":link.id,"message":f"{link.fulfilled_qty}>{link.allocated_qty}"})
    # Products lacking operational configuration
    active_products=db.scalars(select(Product).where(Product.active==1)).all()
    supplier_linked=set(db.scalars(select(SupplierProduct.product_id).where(SupplierProduct.active==1)).all())
    for p in active_products:
        if p.price_ht<=0:
            warnings.append({"type":"PRICE_MISSING","entity":"product","id":p.id,"message":p.name})
        if p.id not in supplier_linked:
            warnings.append({"type":"SUPPLIER_MISSING","entity":"product","id":p.id,"message":p.name})
    return {"ok":len(issues)==0,"blocking_count":len(issues),"warning_count":len(warnings),"issues":issues[:200],"warnings":warnings[:300]}

def schema_status():
    inspector=inspect(engine)
    existing=set(inspector.get_table_names())
    expected=set(Base.metadata.tables.keys())
    missing=sorted(expected-existing)
    alembic_present="alembic_version" in existing
    version=None
    if alembic_present:
        try:
            with engine.connect() as conn:
                version=conn.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 1").scalar()
        except Exception:
            version=None
    return {
        "expected_tables":len(expected),
        "existing_tables":len(existing & expected),
        "missing_tables":missing,
        "alembic_version":version,
        "alembic_present":alembic_present,
        "schema_ready":not missing and (alembic_present if ENVIRONMENT=="production" else True)
    }

def production_config_errors():
    errors=[]
    if ENVIRONMENT=="production":
        if not DATABASE_URL.startswith("postgresql"):
            errors.append("DATABASE_URL doit pointer vers PostgreSQL en production.")
        if SECRET_KEY=="CHANGE-ME-IN-RENDER" or len(SECRET_KEY)<32:
            errors.append("SECRET_KEY de production manquante ou trop courte.")
        if SEED_DEMO_DATA:
            errors.append("SEED_DEMO_DATA doit être false en production.")
        if AUTO_CREATE_SCHEMA:
            errors.append("AUTO_CREATE_SCHEMA doit être false en production ; utilisez Alembic.")
        if "*" in ALLOWED_ORIGINS:
            errors.append("ALLOWED_ORIGINS ne doit pas contenir * en production.")
        if any("YOUR-PRODUCTION-DOMAIN" in x for x in ALLOWED_ORIGINS):
            errors.append("ALLOWED_ORIGINS contient encore le domaine exemple.")
        if not SITE_URL or "YOUR-PRODUCTION-DOMAIN" in SITE_URL:
            errors.append("SITE_URL doit contenir le vrai domaine public.")
        if not BOOTSTRAP_ADMIN_EMAIL or "YOUR-DOMAIN" in BOOTSTRAP_ADMIN_EMAIL:
            errors.append("BOOTSTRAP_ADMIN_EMAIL doit être remplacé par un vrai e-mail.")
        if not BOOTSTRAP_ADMIN_PASSWORD or len(BOOTSTRAP_ADMIN_PASSWORD)<12:
            errors.append("BOOTSTRAP_ADMIN_PASSWORD doit contenir au moins 12 caractères.")
    return errors

def seed():
    if AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if SEED_DEMO_DATA:
            required_demo=[DEMO_ADMIN_EMAIL,DEMO_ADMIN_PASSWORD,DEMO_PRO_EMAIL,DEMO_PRO_PASSWORD,DEMO_B2C_EMAIL,DEMO_B2C_PASSWORD]
            if not all(required_demo):
                raise RuntimeError("SEED_DEMO_DATA=true exige les variables DEMO_* explicites.")
            if not db.scalar(select(User).where(func.lower(User.email)==DEMO_ADMIN_EMAIL)):
                db.add(User(email=DEMO_ADMIN_EMAIL,password_hash=pwd.hash(DEMO_ADMIN_PASSWORD),full_name="Administrateur Le Panier Frais Bio",role="ADMIN",active=1,created_at=datetime.now(timezone.utc).isoformat()))
            if not db.scalar(select(Client).where(Client.name=="Restaurant Démo")):
                db.add_all([Client(client_type="PRO",name="Restaurant Démo",email=DEMO_PRO_EMAIL),Client(client_type="B2C",name="Client Démo",email=DEMO_B2C_EMAIL)])
            db.flush()
            pro_client=db.scalar(select(Client).where(Client.name=="Restaurant Démo"))
            pro_user=db.scalar(select(User).where(func.lower(User.email)==DEMO_PRO_EMAIL))
            if not pro_user:
                pro_user=User(email=DEMO_PRO_EMAIL,password_hash=pwd.hash(DEMO_PRO_PASSWORD),full_name="Restaurant Démo",role="PRO",active=1,created_at=datetime.now(timezone.utc).isoformat()); db.add(pro_user); db.flush()
            if pro_client and pro_user and not db.scalar(select(ProUserLink).where(ProUserLink.user_id==pro_user.id)):
                db.add(ProUserLink(user_id=pro_user.id,client_id=pro_client.id))
            if pro_client and not db.scalar(select(ProRestaurantProfile).where(ProRestaurantProfile.client_id==pro_client.id)):
                db.add(ProRestaurantProfile(client_id=pro_client.id,covers_lunch=35,covers_dinner=45,delivery_days="Mardi, Vendredi",default_pack_kg=2.5,prep_hour_cost=20.0,prep_minutes_per_kg=12.0,notes="Profil de démonstration — paramètres modifiables par le restaurant."))
            b2c_client=db.scalar(select(Client).where(Client.name=="Client Démo"))
            b2c_user=db.scalar(select(User).where(func.lower(User.email)==DEMO_B2C_EMAIL))
            if not b2c_user:
                b2c_user=User(email=DEMO_B2C_EMAIL,password_hash=pwd.hash(DEMO_B2C_PASSWORD),full_name="Client Démo",role="CUSTOMER",active=1,created_at=datetime.now(timezone.utc).isoformat()); db.add(b2c_user); db.flush()
            if b2c_client and b2c_user and not db.scalar(select(B2CUserLink).where(B2CUserLink.user_id==b2c_user.id)):
                db.add(B2CUserLink(user_id=b2c_user.id,client_id=b2c_client.id))
            if b2c_client and not db.scalar(select(B2CProfile).where(B2CProfile.client_id==b2c_client.id)):
                db.add(B2CProfile(client_id=b2c_client.id,household_size=2,weekly_budget=45.0,goals="Manger équilibré, gagner du temps",favorite_pickup_slot="18:00 - 19:00",preferred_mode="CLICK_COLLECT",loyalty_points=120))
            if b2c_client and not db.scalar(select(B2CSubscription).where(B2CSubscription.client_id==b2c_client.id)):
                db.add(B2CSubscription(client_id=b2c_client.id,name="Panier frais semaine",frequency="HEBDOMADAIRE",budget=35.0,pickup_day="Vendredi",active=1))
        if BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD and not db.scalar(select(User).where(func.lower(User.email)==BOOTSTRAP_ADMIN_EMAIL)):
            db.add(User(email=BOOTSTRAP_ADMIN_EMAIL,password_hash=pwd.hash(BOOTSTRAP_ADMIN_PASSWORD),full_name=BOOTSTRAP_ADMIN_NAME,role="ADMIN",active=1,created_at=datetime.now(timezone.utc).isoformat()))
        if not db.scalar(select(Product).where(Product.reference=="LPFB-CAR-001")):
            carrot=Product(reference="LPFB-CAR-001",name="Carottes bio",family="Légumes préparés",unit="kg",price_ht=6.90,active=1)
            green=Product(reference="LPFB-GRN-033",name="THE GREEN 33 cl",family="Jus",unit="bouteille",price_ht=4.50,active=1)
            salad=Product(reference="LPFB-SAL-JUS",name="Formule salade + jus",family="Formules",unit="formule",price_ht=6.36,active=1)
            db.add_all([carrot,green,salad]); db.flush()
            db.add_all([ProductCut(product_id=carrot.id,cut_name=x,yield_rate=y,extra_price_ht=e) for x,y,e in [("Rondelles",.88,.30),("Bâtonnets",.86,.40),("Julienne",.84,.50),("Dés",.85,.45),("Râpée",.90,.35)]])
            if SEED_DEMO_DATA:
                db.add_all([
                    Lot(product_id=carrot.id,internal_lot="CAR-A12",supplier_lot="FOUR-2026-A",qty_received=25,expiry_date="2026-09-22",status="LIBERE"),
                    Lot(product_id=carrot.id,internal_lot="CAR-A13",supplier_lot="FOUR-2026-B",qty_received=35,expiry_date="2026-09-25",status="LIBERE"),
                    Lot(product_id=carrot.id,internal_lot="CAR-X99",supplier_lot="FOUR-2026-X",qty_received=12,expiry_date="2026-09-21",status="BLOQUE")])
        # Visuels de marque par défaut — configurables ensuite dans le back-office
        media_defaults=[
            ("LPFB-GRN-033","/assets/jus-shots-lpfb.webp","Jus et shots Le Panier Frais Bio"),
            ("LPFB-SAL-JUS","/assets/poke-bowls-lpfb.webp","Formule salade et jus Le Panier Frais Bio"),
        ]
        for ref,url,alt in media_defaults:
            p=db.scalar(select(Product).where(Product.reference==ref))
            if p and not db.scalar(select(ProductMedia).where(ProductMedia.product_id==p.id)):
                db.add(ProductMedia(product_id=p.id,image_url=url,alt_text=alt,badge="Le Panier Frais Bio",active=1))
        if not db.scalar(select(MarketingVisual).limit(1)):
            db.add_all([
                MarketingVisual(placement="HOME_FEATURED",title="Poke Bowls Signature",subtitle="Des recettes fraîches et colorées.",image_url="/assets/poke-bowls-lpfb.webp",target_filter="salade",active=1,sort_order=10),
                MarketingVisual(placement="HOME_FEATURED",title="Jus & shots",subtitle="Formats fraîcheur et bien-être.",image_url="/assets/jus-shots-lpfb.webp",target_filter="jus",active=1,sort_order=20),
                MarketingVisual(placement="HOME_INSPIRATION",title="Gamme bien-être",subtitle="Jus, shots et formats nomades.",image_url="/assets/bien-etre-lpfb.webp",target_filter="jus",active=1,sort_order=30),
                MarketingVisual(placement="PRO_HERO",title="Préparation PRO",subtitle="Fruits et légumes préparés pour les cuisines professionnelles.",image_url="/assets/pro-preparation-lpfb.webp",target_filter="",active=1,sort_order=10)
            ])
        if not db.scalar(select(Supplier).limit(1)):
            db.add_all([
                Supplier(name="Coopérative Bio d'Île-de-France",city="Combs-la-Ville (77)",specialty="Fruits, légumes, 4e/5e gamme, légumineuses"),
                Supplier(name="GAEC de la Ronce",city="Marcoussis (91)",specialty="Maraîchage bio"),
                Supplier(name="Ferme de Bruille",city="La Croix-en-Brie (77)",specialty="Fruits et légumes bio, pommes de terre, carottes, betteraves, jus")])
        if not db.scalar(select(Equipment).limit(1)):
            db.add_all([
                Equipment(name="Machine à découpe légumes",budget_low=1500,budget_high=1500),
                Equipment(name="Machine d'emballage / sous-vide",budget_low=1200,budget_high=2000),
                Equipment(name="Table inox professionnelle",budget_low=700,budget_high=1000),
                Equipment(name="Point lavage / plonge inox",budget_low=900,budget_high=1300),
                Equipment(name="Chambre froide positive",budget_low=3800,budget_high=6000),
                Equipment(name="Frigo vitrine linéaire fin",budget_low=3000,budget_high=6000),
                Equipment(name="Rack / étagères",budget_low=500,budget_high=900),
                Equipment(name="Poubelles professionnelles",budget_low=250,budget_high=500)])
        # Catalogue maître extensible : les références ci-dessous peuvent être commandées même sans stock.
        # Prix 0 = prix à confirmer avant validation commerciale.
        master_produce = [
            # Racines, bulbes, tubercules
            ("LPFB-AIL-001","Ail","Légumes"),("LPFB-ECH-001","Échalote","Légumes"),("LPFB-OIGR-001","Oignon rouge","Légumes"),
            ("LPFB-OIGJ-001","Oignon jaune","Légumes"),("LPFB-RAD-001","Radis rose","Légumes"),("LPFB-RADN-001","Radis noir","Légumes"),
            ("LPFB-RADBL-001","Radis blanc / daikon","Légumes"),("LPFB-NAV-002","Navet boule d'or","Légumes"),("LPFB-RUT-001","Rutabaga","Légumes"),
            ("LPFB-TOP-001","Topinambour","Légumes"),("LPFB-PATD-001","Patate douce","Légumes"),("LPFB-MANIOC-001","Manioc","Légumes"),
            ("LPFB-IGN-001","Igname","Légumes"),("LPFB-TARO-001","Taro","Légumes"),("LPFB-RAIF-001","Raifort","Légumes"),
            # Choux, feuilles, salades
            ("LPFB-CHOR-001","Chou rouge","Légumes"),("LPFB-CHOV-001","Chou vert","Légumes"),("LPFB-CHOF-001","Chou frisé","Légumes"),
            ("LPFB-CHOBR-001","Chou de Bruxelles","Légumes"),("LPFB-CHOC-001","Chou chinois","Légumes"),("LPFB-PAK-001","Pak choï","Légumes"),
            ("LPFB-ROM-001","Laitue romaine","Légumes"),("LPFB-BAT-001","Batavia","Légumes"),("LPFB-FEUCH-001","Feuille de chêne","Légumes"),
            ("LPFB-ROQ-001","Roquette","Légumes"),("LPFB-CRES-001","Cresson","Légumes"),("LPFB-BLET-001","Blette","Légumes"),
            ("LPFB-OSE-001","Oseille","Légumes"),("LPFB-END-001","Endive","Légumes"),("LPFB-RADIC-001","Radicchio","Légumes"),
            # Légumes fruits
            ("LPFB-TOMC-001","Tomate cerise","Légumes"),("LPFB-TOMG-001","Tomate grappe","Légumes"),("LPFB-TOMAN-001","Tomate ancienne","Légumes"),
            ("LPFB-POIVR-001","Poivron rouge","Légumes"),("LPFB-POIVJ-001","Poivron jaune","Légumes"),("LPFB-POIVV-001","Poivron vert","Légumes"),
            ("LPFB-PIM-001","Piment frais","Légumes"),("LPFB-OKR-001","Gombo","Légumes"),("LPFB-CHAY-001","Chayote / christophine","Légumes"),
            ("LPFB-CITR-001","Citrouille","Légumes"),("LPFB-BUT-001","Courge butternut","Légumes"),("LPFB-POTIR-001","Potiron","Légumes"),
            ("LPFB-SPAG-001","Courge spaghetti","Légumes"),("LPFB-PATIS-001","Pâtisson","Légumes"),
            # Tiges, fleurs, autres légumes
            ("LPFB-ASPV-001","Asperge verte","Légumes"),("LPFB-ASPB-001","Asperge blanche","Légumes"),("LPFB-ART-001","Artichaut","Légumes"),
            ("LPFB-CELB-001","Céleri branche","Légumes"),("LPFB-RHUB-001","Rhubarbe","Légumes"),("LPFB-MAIS-001","Maïs doux","Légumes"),
            ("LPFB-PETP-001","Petit pois","Légumes"),("LPFB-FEV-001","Fève","Légumes"),("LPFB-POIG-001","Pois gourmand","Légumes"),
            ("LPFB-SOJ-001","Edamame","Légumes"),("LPFB-FEN2-001","Fenouil","Légumes"),
            # Champignons
            ("LPFB-PLEU-001","Pleurote","Champignons"),("LPFB-SHI-001","Shiitaké","Champignons"),("LPFB-PORC-001","Cèpe","Champignons"),
            ("LPFB-GIR-001","Girolle","Champignons"),("LPFB-PORTO-001","Portobello","Champignons"),
            # Fruits à pépins, noyaux, raisins
            ("LPFB-POMR-001","Pomme rouge","Fruits"),("LPFB-POMV-001","Pomme verte","Fruits"),("LPFB-POIR-002","Poire conférence","Fruits"),
            ("LPFB-PECH-001","Pêche","Fruits"),("LPFB-NECT-001","Nectarine","Fruits"),("LPFB-ABR-001","Abricot","Fruits"),
            ("LPFB-PRU-001","Prune","Fruits"),("LPFB-MIR-001","Mirabelle","Fruits"),("LPFB-CER-001","Cerise","Fruits"),
            ("LPFB-RAIV-001","Raisin blanc","Fruits"),("LPFB-RAIR-001","Raisin rouge","Fruits"),
            # Agrumes
            ("LPFB-MAND-001","Mandarine","Fruits"),("LPFB-PAMP-001","Pamplemousse","Fruits"),("LPFB-POMELO-001","Pomelo","Fruits"),
            ("LPFB-CITV-001","Citron vert","Fruits"),("LPFB-KUM-001","Kumquat","Fruits"),("LPFB-BERG-001","Bergamote","Fruits"),
            # Fruits rouges
            ("LPFB-MUR-001","Mûre","Fruits rouges"),("LPFB-GRO-001","Groseille","Fruits rouges"),("LPFB-CASS-001","Cassis","Fruits rouges"),
            ("LPFB-AIR-001","Airelle","Fruits rouges"),("LPFB-CRAN-001","Cranberry fraîche","Fruits rouges"),
            # Melons et apparentés
            ("LPFB-MELCH-001","Melon charentais","Fruits"),("LPFB-MELJ-001","Melon jaune","Fruits"),
            # Tropicaux / exotiques
            ("LPFB-GOY-001","Goyave","Fruits"),("LPFB-PAP-001","Papaye","Fruits"),("LPFB-GRE-001","Grenade","Fruits"),
            ("LPFB-PASS-001","Fruit de la passion","Fruits"),("LPFB-LYC-001","Litchi","Fruits"),("LPFB-KAK-001","Kaki","Fruits"),
            ("LPFB-FIG-001","Figue","Fruits"),("LPFB-DAT-001","Datte fraîche","Fruits"),("LPFB-COCO-001","Noix de coco","Fruits"),
            ("LPFB-CARAM-001","Carambole","Fruits"),("LPFB-PIT-001","Pitaya / fruit du dragon","Fruits"),("LPFB-MANGOS-001","Mangoustan","Fruits"),
            ("LPFB-RAMB-001","Ramboutan","Fruits"),("LPFB-JACK-001","Jacquier","Fruits"),("LPFB-CORO-001","Corossol","Fruits"),
            ("LPFB-CACH-001","Cachiman","Fruits"),("LPFB-TAM-001","Tamarin","Fruits"),("LPFB-PLAN-001","Banane plantain","Fruits"),
            # Fruits à coque
            ("LPFB-NOI-001","Noix","Fruits à coque"),("LPFB-NOISET-001","Noisette","Fruits à coque"),("LPFB-AMA-001","Amande","Fruits à coque"),
            ("LPFB-CHAT-001","Châtaigne","Fruits à coque"),("LPFB-PIST-001","Pistache fraîche","Fruits à coque"),
            # Aromatiques frais
            ("LPFB-BASIL-001","Basilic frais","Aromatiques"),("LPFB-PERS-001","Persil frais","Aromatiques"),("LPFB-CORI-001","Coriandre fraîche","Aromatiques"),
            ("LPFB-MENTH-001","Menthe fraîche","Aromatiques"),("LPFB-CIB-001","Ciboulette","Aromatiques"),("LPFB-ANETH-001","Aneth","Aromatiques"),
            ("LPFB-THYM-001","Thym frais","Aromatiques"),("LPFB-ROMA-001","Romarin frais","Aromatiques"),("LPFB-ESTR-001","Estragon","Aromatiques"),
            ("LPFB-GING-001","Gingembre frais","Aromatiques"),("LPFB-CURC-001","Curcuma frais","Aromatiques")
        ]
        for ref,name,family in master_produce:
            p=db.scalar(select(Product).where(Product.reference==ref))
            if not p:
                p=Product(reference=ref,name=name,family=family,unit="kg",price_ht=0,active=1); db.add(p); db.flush()
            if not db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==p.id)):
                db.add(ProductAvailability(product_id=p.id,order_mode="SUR_COMMANDE",supplier_lead_days=2,allow_order=1,notes="Référencé au catalogue. Approvisionnement fournisseur à confirmer."))
        # Référentiel élargi fruits & légumes couramment commercialisés en France
        catalog = [
            ("LPFB-TOM-001","Tomate bio","Légumes",4.90,["Rondelles","Dés","Quartiers"]),
            ("LPFB-COU-001","Courgette bio","Légumes",4.50,["Rondelles","Dés","Julienne","Demi-lunes"]),
            ("LPFB-CON-001","Concombre bio","Légumes",4.20,["Rondelles","Dés","Bâtonnets","Lamelles"]),
            ("LPFB-POI-001","Poivron bio","Légumes",6.90,["Lanières","Dés","Julienne"]),
            ("LPFB-OIG-001","Oignon bio","Légumes",3.90,["Émincé","Dés","Rondelles"]),
            ("LPFB-PDT-001","Pomme de terre bio","Légumes",3.80,["Cubes","Quartiers","Rondelles","Bâtonnets"]),
            ("LPFB-BET-001","Betterave bio","Légumes",4.60,["Dés","Julienne","Rondelles","Râpée"]),
            ("LPFB-NAV-001","Navet bio","Légumes",4.20,["Cubes","Quartiers","Julienne"]),
            ("LPFB-PAN-001","Panais bio","Légumes",5.40,["Bâtonnets","Rondelles","Dés"]),
            ("LPFB-CEL-001","Céleri-rave bio","Légumes",5.30,["Râpé","Julienne","Dés"]),
            ("LPFB-POI-002","Poireau bio","Légumes",4.80,["Rondelles","Émincé"]),
            ("LPFB-FEN-001","Fenouil bio","Légumes",5.90,["Émincé","Quartiers"]),
            ("LPFB-BRO-001","Brocoli bio","Légumes",6.50,["Fleurettes","Tiges"]),
            ("LPFB-CHF-001","Chou-fleur bio","Légumes",6.20,["Fleurettes","Râpé"]),
            ("LPFB-CHO-001","Chou blanc bio","Légumes",4.00,["Émincé","Julienne"]),
            ("LPFB-KAL-001","Chou kale bio","Légumes",7.20,["Émincé","Feuilles"]),
            ("LPFB-EPI-001","Épinards bio","Légumes",7.50,["Feuilles"]),
            ("LPFB-SAL-001","Salade verte bio","Légumes",3.50,["Feuilles","Émincée"]),
            ("LPFB-MAC-001","Mâche bio","Légumes",9.50,["Feuilles"]),
            ("LPFB-AUB-001","Aubergine bio","Légumes",5.70,["Dés","Rondelles","Lamelles"]),
            ("LPFB-POT-001","Potimarron bio","Légumes",4.90,["Cubes","Quartiers"]),
            ("LPFB-HAR-001","Haricot vert bio","Légumes",8.90,["Entier","Tronçons"]),
            ("LPFB-CHA-001","Champignon de Paris bio","Légumes",8.50,["Émincé","Quartiers"]),
            ("LPFB-POM-001","Pomme bio","Fruits",4.20,["Quartiers","Dés","Lamelles"]),
            ("LPFB-POI-F01","Poire bio","Fruits",4.90,["Quartiers","Dés","Lamelles"]),
            ("LPFB-ORA-001","Orange bio","Fruits",4.20,["Quartiers","Segments"]),
            ("LPFB-CIT-001","Citron bio","Fruits",5.50,["Rondelles","Quartiers"]),
            ("LPFB-CLE-001","Clémentine bio","Fruits",5.20,["Segments"]),
            ("LPFB-BAN-001","Banane bio","Fruits",3.20,["Rondelles"]),
            ("LPFB-ANA-001","Ananas","Fruits",5.90,["Tranches","Dés","Bâtonnets"]),
            ("LPFB-MAN-001","Mangue","Fruits",7.90,["Dés","Lamelles"]),
            ("LPFB-KIW-001","Kiwi","Fruits",6.50,["Rondelles","Dés"]),
            ("LPFB-RAI-001","Raisin","Fruits",6.90,["Grains"]),
            ("LPFB-FRA-001","Fraise","Fruits rouges",10.90,["Entière","Quartiers"]),
            ("LPFB-FRA-002","Framboise","Fruits rouges",15.90,["Entière"]),
            ("LPFB-MYR-001","Myrtille","Fruits rouges",16.90,["Entière"]),
            ("LPFB-MEL-001","Melon","Fruits",4.90,["Dés","Tranches","Billes"]),
            ("LPFB-PAS-001","Pastèque","Fruits",3.90,["Dés","Tranches","Bâtonnets"]),
            ("LPFB-AVO-001","Avocat","Fruits",7.50,["Lamelles","Dés"]),
        ]
        for ref,name,family,price,cuts in catalog:
            p=db.scalar(select(Product).where(Product.reference==ref))
            if not p:
                p=Product(reference=ref,name=name,family=family,unit="kg",price_ht=price,active=1); db.add(p); db.flush()
            if not db.scalar(select(ProductCut).where(ProductCut.product_id==p.id)):
                for cut in cuts: db.add(ProductCut(product_id=p.id,cut_name=cut,yield_rate=.88,extra_price_ht=.35))
        for p in db.scalars(select(Product)).all():
            if not db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==p.id)):
                db.add(ProductAvailability(product_id=p.id,order_mode="SUR_COMMANDE",supplier_lead_days=2,allow_order=1,notes="Commande autorisée sous réserve d'approvisionnement."))
        # Référentiel portions, usages et recettes (données de départ modifiables)
        if not db.scalar(select(PackagingFormat).limit(1)):
            db.add_all([
                PackagingFormat(segment="B2C",label="Solo",quantity_g=250,recommended_use="1 personne, crudités, garniture ou petit besoin"),
                PackagingFormat(segment="B2C",label="Duo",quantity_g=500,recommended_use="2 personnes, format cœur de gamme"),
                PackagingFormat(segment="B2C",label="Famille",quantity_g=750,recommended_use="3 à 4 personnes"),
                PackagingFormat(segment="B2C",label="Batch",quantity_g=1000,recommended_use="famille, soupe ou batch cooking"),
                PackagingFormat(segment="PRO",label="Test / petite rotation",quantity_g=1000,recommended_use="petit restaurant ou faible rotation"),
                PackagingFormat(segment="PRO",label="Standard cuisine",quantity_g=2500,recommended_use="format principal pour service quotidien"),
                PackagingFormat(segment="PRO",label="Volume",quantity_g=5000,recommended_use="restaurant à rotation régulière"),
                PackagingFormat(segment="PRO",label="Gros volume",quantity_g=10000,recommended_use="collectivité, traiteur, événement, sur commande")])
        if not db.scalar(select(PreparationProfile).limit(1)):
            product_map={x.name:x for x in db.scalars(select(Product)).all()}
            car=product_map.get("Carottes bio")
            if car:
                db.add_all([
                    PreparationProfile(product_id=car.id,cut_name="Râpée",portion_g=90,yield_rate=.90,uses="crudités, salade, sandwich"),
                    PreparationProfile(product_id=car.id,cut_name="Julienne",portion_g=100,yield_rate=.84,uses="wok, garniture, salade"),
                    PreparationProfile(product_id=car.id,cut_name="Bâtonnets",portion_g=120,yield_rate=.86,uses="snacking, cuisson, accompagnement"),
                    PreparationProfile(product_id=car.id,cut_name="Rondelles",portion_g=140,yield_rate=.88,uses="cuisson, potage, accompagnement")])
        if not db.scalar(select(Recipe).limit(1)):
            product_map={x.name:x for x in db.scalars(select(Product)).all()}
            car=product_map.get("Carottes bio")
            r=Recipe(name="Crudités carottes",category="Accompagnement",default_servings=2,description="Préparation froide simple, portion ajustable.")
            db.add(r); db.flush()
            if car: db.add(RecipeIngredient(recipe_id=r.id,product_id=car.id,grams_per_serving=90,cut_name="Râpée"))
        if SEED_DEMO_DATA:
            if not db.scalar(select(ProOrderTemplate).limit(1)):
                pro_client=db.scalar(select(Client).where(Client.client_type=="PRO"))
                car=db.scalar(select(Product).where(Product.reference=="LPFB-CAR-001"))
                cou=db.scalar(select(Product).where(Product.reference=="LPFB-COU-001"))
                oig=db.scalar(select(Product).where(Product.reference=="LPFB-OIG-001"))
                if pro_client and car:
                    tpl=ProOrderTemplate(client_id=pro_client.id,name="Mise en place hebdomadaire",delivery_mode="LIVRAISON",active=1)
                    db.add(tpl); db.flush()
                    for prod,qty,cut,pack in [(car,5,"Julienne",2.5),(cou,5,"Rondelles",2.5),(oig,2.5,"Émincé",2.5)]:
                        if prod: db.add(ProOrderTemplateLine(template_id=tpl.id,product_id=prod.id,quantity_kg=qty,cut_name=cut,pack_size_kg=pack))
        defaults={"company_name":"Le Panier Frais Bio","store_area_m2":"29","investment_budget":"40000","social_formula":"Salade + jus : 7 €","click_collect":"Actif","maintenance_mode":"false","maintenance_message":"Le service est temporairement en maintenance.","legal_notice_status":"A_COMPLETER","privacy_notice_status":"A_COMPLETER"}
        for k,v in defaults.items():
            if not db.scalar(select(AppSetting).where(AppSetting.key==k)): db.add(AppSetting(key=k,value=v))
        db.flush()
        reconcile_legacy_lot_stages(db)
        db.commit()

@app.on_event("startup")
def startup():
    errors=production_config_errors()
    if ENVIRONMENT=="production" and PRODUCTION_STRICT and errors:
        raise RuntimeError("Configuration production invalide: "+" | ".join(errors))
    if ENVIRONMENT=="production":
        schema=schema_status()
        if not schema["schema_ready"]:
            raise RuntimeError("Schéma base non migré: "+", ".join(schema["missing_tables"][:20])+" | alembic_version="+str(schema["alembic_version"]))
    seed()

class LoginIn(BaseModel): email:str; password:str
class ClientIn(BaseModel): client_type:str; name:str; email:Optional[str]=None
class StaffUserCreateIn(BaseModel):
    email:str=Field(min_length=5,max_length=255)
    full_name:str=Field(min_length=2,max_length=255)
    role:str=Field(max_length=50)
    password:str=Field(min_length=10,max_length=200)

class StaffUserUpdateIn(BaseModel):
    full_name:str=Field(min_length=2,max_length=255)
    role:str=Field(max_length=50)
    active:bool=True

class StaffPasswordResetIn(BaseModel):
    password:str=Field(min_length=10,max_length=200)

class PreproductionSmokeTestIn(BaseModel):
    include_write_cycle:bool=True

class ProductMediaIn(BaseModel):
    product_id:int
    image_url:str=Field(min_length=2,max_length=1000)
    alt_text:str=Field(default="",max_length=255)
    badge:str=Field(default="Le Panier Frais Bio",max_length=100)
    active:bool=True

class MarketingVisualIn(BaseModel):
    placement:str=Field(min_length=2,max_length=80)
    title:str=Field(min_length=2,max_length=255)
    subtitle:str=Field(default="",max_length=500)
    image_url:str=Field(min_length=2,max_length=1000)
    target_filter:str=Field(default="",max_length=255)
    active:bool=True
    sort_order:int=0

class ProcurementStatusIn(BaseModel):
    status:str=Field(max_length=40)

class ProcurementConvertLineIn(BaseModel):
    request_id:int
    supplier_id:int
    unit_price_ht:float=Field(default=0,ge=0)

class ProcurementConvertIn(BaseModel):
    expected_date:Optional[str]=None
    note:str=""
    lines:list[ProcurementConvertLineIn]

class ProductAvailabilityIn(BaseModel):
    order_mode:str=Field(default="SUR_COMMANDE",max_length=40)
    supplier_lead_days:int=Field(default=2,ge=0,le=90)
    allow_order:bool=True
    notes:str=Field(default="",max_length=500)

class GeneralSourcingRequestIn(BaseModel):
    requested_name:str=Field(min_length=2,max_length=255)
    category:str=Field(default="Fruits & légumes",max_length=100)
    quantity_text:str=Field(default="",max_length=100)
    customer_email:Optional[str]=Field(default=None,max_length=255)
    note:str=Field(default="",max_length=1000)

class SelfPasswordChangeIn(BaseModel):
    current_password:str=Field(min_length=1,max_length=200)
    new_password:str=Field(min_length=12,max_length=200)

class MaintenanceModeIn(BaseModel):
    enabled:bool
    message:str=Field(default="Le service est temporairement en maintenance.",max_length=500)

class ProductSourcingRequestIn(BaseModel):
    product_id:int
    customer_email:Optional[str]=Field(default=None,max_length=255)
    quantity:float=Field(default=1,gt=0)
    note:str=Field(default="",max_length=1000)

class ProductIn(BaseModel): reference:str; name:str; family:str="Fruits & légumes"; unit:str="kg"; price_ht:float=Field(ge=0)
class ProductCostIn(BaseModel):
    purchase_cost_ht:float=Field(default=0,ge=0)
    packaging_cost_ht:float=Field(default=0,ge=0)
    labor_cost_ht:float=Field(default=0,ge=0)
    other_cost_ht:float=Field(default=0,ge=0)
    target_margin_pct:float=Field(default=35,ge=0,le=95)

class ProductTaxIn(BaseModel):
    tax_rate_pct:float=Field(ge=0,le=100)
    tax_label:str=Field(default="Taux configuré",max_length=100)

class InvoiceFinalizeIn(BaseModel):
    due_date:Optional[str]=Field(default=None,max_length=20)

class PaymentMarkIn(BaseModel):
    method:str=Field(default="SUR_PLACE",max_length=50)
    reference:Optional[str]=Field(default=None,max_length=100)

class CreditNoteIn(BaseModel):
    reason:str=Field(min_length=2,max_length=500)
    amount_ht:float=Field(gt=0)

class ProductPriceUpdateIn(BaseModel):
    price_ht:float=Field(ge=0)
    reason:str=Field(default="",max_length=500)

class LotIn(BaseModel): product_id:int; internal_lot:str; supplier_lot:Optional[str]=None; qty_received:float=Field(gt=0); expiry_date:Optional[str]=None; status:str="LIBERE"
class ProductionCompleteIn(BaseModel):
    internal_lot:str=Field(min_length=2,max_length=100)
    actual_input_qty:float=Field(gt=0)
    actual_output_qty:float=Field(gt=0)
    cut_name:Optional[str]=Field(default=None,max_length=100)
    packaging:str=Field(default="À définir",max_length=100)
    expiry_date:Optional[str]=Field(default=None,max_length=20)
    temperature_c:Optional[float]=Field(default=None,ge=-50,le=100)
    quality_status:str=Field(default="VALIDEE",max_length=30)
    operator_notes:str=Field(default="",max_length=1000)

class OrderIn(BaseModel): client_id:int; product_id:int; quantity:float=Field(gt=0); delivery_mode:str="LIVRAISON"; cut_name:Optional[str]=None; note:Optional[str]=None
class ProductionIn(BaseModel): product_id:int; quantity_needed:float=Field(gt=0); source_order_id:Optional[int]=None
class SupplierCoverageBulkIn(BaseModel):
    supplier_id:int
    product_ids:list[int]
    lead_time_days:int=Field(default=2,ge=0,le=365)
    note_reference:Optional[str]=None

class SupplierProductIn(BaseModel):
    supplier_id:int
    product_id:int
    supplier_reference:Optional[str]=None
    last_price_ht:float=Field(default=0,ge=0)
    min_order_qty:float=Field(default=0,ge=0)
    lead_time_days:int=Field(default=0,ge=0,le=365)

class PurchaseOrderLineIn(BaseModel):
    product_id:int
    quantity:float=Field(gt=0)
    unit_price_ht:float=Field(default=0,ge=0)

class PurchaseOrderIn(BaseModel):
    supplier_id:int
    expected_date:Optional[str]=None
    note:str=""
    lines:list[PurchaseOrderLineIn]

class PurchaseReceiptLineIn(BaseModel):
    purchase_order_line_id:int
    received_qty:float=Field(gt=0)
    internal_lot:str=Field(min_length=2,max_length=100)
    supplier_lot:Optional[str]=None
    expiry_date:Optional[str]=None
    lot_status:str=Field(default="BLOQUE",max_length=30)

class PurchaseReceiptIn(BaseModel):
    note:str=""
    lines:list[PurchaseReceiptLineIn]

class SupplierIn(BaseModel): name:str; city:Optional[str]=None; specialty:Optional[str]=None
class EquipmentIn(BaseModel): name:str; budget_low:float=0; budget_high:float=0; priority:str="INDISPENSABLE"; status:str="A_ACHETER"
class SettingIn(BaseModel): value:str
class PortionCalcIn(BaseModel):
    product_id:int
    servings:int=Field(ge=1,le=500)
    cut_name:Optional[str]=None
    grams_per_serving:Optional[float]=Field(default=None,gt=0)

class ProCalcIn(BaseModel):
    product_id:int
    covers:int=Field(ge=1,le=5000)
    grams_per_cover:float=Field(gt=0)
    cut_name:Optional[str]=None

class ProBatchLineIn(BaseModel):
    product_id:int
    quantity_kg:float=Field(gt=0)
    cut_name:Optional[str]=None
    pack_size_kg:Optional[float]=Field(default=2.5,gt=0)
    note:Optional[str]=None

class ProBatchOrderIn(BaseModel):
    client_id:int
    delivery_mode:str="LIVRAISON"
    lines:list[ProBatchLineIn]
    note:Optional[str]=None

class ProTemplateIn(BaseModel):
    client_id:int
    name:str
    delivery_mode:str="LIVRAISON"
    lines:list[ProBatchLineIn]

class RecipeCalcIn(BaseModel):
    recipe_id:int
    servings:int=Field(ge=1,le=500)


def make_token(user):
    return jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(minutes=TOKEN_TTL_MINUTES)},SECRET_KEY,algorithm="HS256")

def current_user(token:str=Depends(oauth),db:Session=Depends(get_db)):
    try: uid=int(jwt.decode(token,SECRET_KEY,algorithms=["HS256"])["sub"])
    except (JWTError,KeyError,ValueError): raise HTTPException(401,"Session invalide")
    user=db.get(User,uid)
    if not user or not user.active: raise HTTPException(401,"Utilisateur inactif")
    return user

def roles(*allowed):
    def guard(user=Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403,"Accès refusé")
        return user
    return guard

def pro_client_for_user(db:Session,user:User):
    if user.role!="PRO": return None
    link=db.scalar(select(ProUserLink).where(ProUserLink.user_id==user.id))
    return db.get(Client,link.client_id) if link else None

@app.get("/app-config")
def app_config():
    with SessionLocal() as db:
        m=maintenance_state(db)
    return {"brand":"Le Panier Frais Bio","site_url":SITE_URL,"schema":schema_status(),"version":"1.0.0","environment":ENVIRONMENT,"demo_enabled":bool(SEED_DEMO_DATA and ENVIRONMENT!="production"),"maintenance":m,"support_email":SUPPORT_EMAIL,"support_phone":SUPPORT_PHONE,"release_channel":RELEASE_CHANNEL,"online_payment_enabled":bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET),"payment_provider":"stripe" if STRIPE_SECRET_KEY else None}

@app.get("/health")
def health(db:Session=Depends(get_db)):
    db.execute(select(1)); return {"status":"ok","version":"1.0.0","database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite"}

@app.get("/health/ready")
def health_ready(db:Session=Depends(get_db)):
    db.execute(select(1))
    errors=production_config_errors()
    schema=schema_status()
    if ENVIRONMENT=="production" and (errors or not schema["schema_ready"]):
        return JSONResponse(status_code=503,content={"status":"not_ready","version":"1.0.0","database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite","schema":schema})
    return {"status":"ready","version":"1.0.0","database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite","schema":schema}

@app.post("/auth/login")
def login(data:LoginIn,db:Session=Depends(get_db)):
    normalized=data.email.strip().lower()
    fingerprint=hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat()
    failed=db.scalar(select(func.count(AuditLog.id)).where(AuditLog.event_type=="LOGIN_FAILED",AuditLog.created_at>=cutoff,AuditLog.details.like(f"%id={fingerprint}%"))) or 0
    if failed>=8:
        audit(db,"LOGIN_BLOCKED",f"id={fingerprint};window=15m");db.commit()
        raise HTTPException(429,"Trop de tentatives. Réessayez dans quelques minutes.")
    user=db.scalar(select(User).where(func.lower(User.email)==normalized))
    valid=pwd.verify(data.password,user.password_hash if user else DUMMY_PASSWORD_HASH)
    if not user or not valid:
        audit(db,"LOGIN_FAILED",f"id={fingerprint}"); db.commit()
        raise HTTPException(401,"Identifiants incorrects")
    audit(db,"LOGIN_SUCCESS",f"user_id={user.id};role={user.role}"); db.commit()
    return {"access_token":make_token(user),"token_type":"bearer","name":user.full_name,"role":user.role}

@app.get("/auth/me")
def me(user=Depends(current_user)): return {"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role}



@app.get("/ops/schema-status")
def ops_schema_status(user=Depends(roles("ADMIN","MANAGER"))):
    return schema_status()

@app.get("/ops/integrity")
def ops_integrity(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    return integrity_report(db)

@app.get("/ops/release-status")
def ops_release_status(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    integ=integrity_report(db)
    readiness=readiness_checks(db) if "readiness_checks" in globals() else {"ready_for_production":False}
    return {
        "version":"1.0.0",
        "channel":RELEASE_CHANNEL,
        "environment":ENVIRONMENT,
        "database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite",
        "integrity":integ,
        "readiness":readiness,
        "maintenance":maintenance_state(db),
        "site_url":SITE_URL,"schema":schema_status(),
        "support_configured":bool(SUPPORT_EMAIL or SUPPORT_PHONE)
    }

@app.get("/ops/audit-summary")
def ops_audit_summary(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    rows=db.execute(select(AuditLog.event_type,func.count(AuditLog.id)).group_by(AuditLog.event_type).order_by(func.count(AuditLog.id).desc())).all()
    return [{"event_type":event,"count":count} for event,count in rows]

@app.get("/ops/role-matrix")
def ops_role_matrix(user=Depends(roles("ADMIN","MANAGER"))):
    return {
      "roles":list(STAFF_ROLES),
      "matrix":{
        "ADMIN":["all"],
        "MANAGER":["dashboard","catalogue","stock","production","orders","clients","suppliers","purchasing","billing","team-read","audit"],
        "VENTE":["dashboard","catalogue","orders","clients","availability","procurement"],
        "PRODUCTION":["stock","production","traceability","receipts"],
        "LIVRAISON":["deliveries","orders-read"],
        "COMPTA":["billing","payments","invoices","costing-read"]
      }
    }

@app.put("/ops/maintenance")
def ops_maintenance(data:MaintenanceModeIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    for key,value in [("maintenance_mode","true" if data.enabled else "false"),("maintenance_message",data.message)]:
        row=db.scalar(select(AppSetting).where(AppSetting.key==key))
        if not row: db.add(AppSetting(key=key,value=value))
        else: row.value=value
    audit(db,"MAINTENANCE_MODE",f"enabled={data.enabled};by={user.email}")
    db.commit()
    return maintenance_state(db)

@app.post("/auth/change-password")
def self_change_password(data:SelfPasswordChangeIn,db:Session=Depends(get_db),user=Depends(current_user)):
    row=db.get(User,user.id)
    if not row or not pwd.verify(data.current_password,row.password_hash):
        raise HTTPException(400,"Mot de passe actuel incorrect")
    if data.current_password==data.new_password:
        raise HTTPException(400,"Le nouveau mot de passe doit être différent")
    row.password_hash=pwd.hash(data.new_password)
    audit(db,"PASSWORD_SELF_CHANGE",f"user_id={row.id}")
    db.commit()
    return {"ok":True}

@app.post("/public/general-sourcing-request")
def public_general_sourcing_request(data:GeneralSourcingRequestIn,db:Session=Depends(get_db)):
    row=GeneralSourcingRequest(
        requested_name=data.requested_name.strip(),
        category=data.category.strip(),
        quantity_text=data.quantity_text.strip(),
        customer_email=(data.customer_email.strip().lower() if data.customer_email else None),
        note=data.note.strip(),
        status="A_TRAITER",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(row); db.commit(); db.refresh(row)
    return {"request_id":row.id,"status":row.status,"message":"Votre demande de produit a été enregistrée. La disponibilité et le prix seront confirmés après sourcing fournisseur."}

@app.get("/sourcing/general")
def general_sourcing_requests(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    rows=db.scalars(select(GeneralSourcingRequest).order_by(GeneralSourcingRequest.id.desc())).all()
    return [{"id":x.id,"requested_name":x.requested_name,"category":x.category,"quantity_text":x.quantity_text,"customer_email":x.customer_email,"note":x.note,"status":x.status,"created_at":x.created_at} for x in rows]

@app.get("/security/status")
def security_status(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    warnings=[]
    if SECRET_KEY=="CHANGE-ME-IN-RENDER": warnings.append("SECRET_KEY utilise encore la valeur de démonstration.")
    if DATABASE_URL.startswith("sqlite"): warnings.append("SQLite détecté : préférer PostgreSQL persistant pour la production.")
    demo_users=db.scalars(select(User).where(User.email.in_([DEMO_ADMIN_EMAIL,DEMO_PRO_EMAIL,DEMO_B2C_EMAIL]))).all()
    if demo_users: warnings.append("Des comptes de démonstration sont encore présents.")
    if ENVIRONMENT=="production" and SEED_DEMO_DATA: warnings.append("SEED_DEMO_DATA est actif en environnement production.")
    active_staff=db.scalar(select(func.count(User.id)).where(User.role.in_(STAFF_ROLES),User.active==1)) or 0
    recent_failures=db.scalar(select(func.count(AuditLog.id)).where(AuditLog.event_type=="LOGIN_FAILED")) or 0
    return {"database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite","secret_key_default":SECRET_KEY=="CHANGE-ME-IN-RENDER","demo_accounts_present":bool(demo_users),"active_staff":active_staff,"login_failures_logged":recent_failures,"environment":ENVIRONMENT,"seed_demo_data":SEED_DEMO_DATA,"production_strict":PRODUCTION_STRICT,"production_config_errors":production_config_errors(),"security_headers":True,"warnings":warnings}

@app.get("/users")
def list_users(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    return [{"id":x.id,"email":x.email,"full_name":x.full_name,"role":x.role,"active":bool(x.active),"created_at":x.created_at} for x in db.scalars(select(User).order_by(User.id)).all()]

@app.post("/users")
def create_staff_user(data:StaffUserCreateIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    role=data.role.upper()
    if role not in MANAGED_STAFF_ROLES: raise HTTPException(400,"Rôle opérationnel invalide")
    email=data.email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email)==email)): raise HTTPException(409,"Adresse e-mail déjà utilisée")
    row=User(email=email,password_hash=pwd.hash(data.password),full_name=data.full_name.strip(),role=role,active=1,created_at=datetime.now(timezone.utc).isoformat())
    db.add(row); db.flush(); audit(db,"USER_CREATE",f"user_id={row.id};email={email};role={role};by={user.email}"); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.put("/users/{user_id}")
def update_staff_user(user_id:int,data:StaffUserUpdateIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    row=db.get(User,user_id)
    if not row: raise HTTPException(404,"Utilisateur introuvable")
    role=data.role.upper()
    if role not in MANAGED_STAFF_ROLES: raise HTTPException(400,"Rôle opérationnel invalide")
    if row.id==user.id and not data.active: raise HTTPException(409,"Vous ne pouvez pas désactiver votre propre compte")
    row.full_name=data.full_name.strip(); row.role=role; row.active=1 if data.active else 0
    audit(db,"USER_UPDATE",f"user_id={row.id};role={role};active={row.active};by={user.email}"); db.commit()
    return {"ok":True}

@app.post("/users/{user_id}/reset-password")
def reset_staff_password(user_id:int,data:StaffPasswordResetIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    row=db.get(User,user_id)
    if not row: raise HTTPException(404,"Utilisateur introuvable")
    if row.role not in STAFF_ROLES: raise HTTPException(409,"Réinitialisation réservée aux comptes équipe dans ce module")
    row.password_hash=pwd.hash(data.password)
    audit(db,"USER_PASSWORD_RESET",f"user_id={row.id};by={user.email}"); db.commit()
    return {"ok":True}

@app.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    products=db.scalar(select(func.count(Product.id)).where(Product.active==1)) or 0
    clients=db.scalar(select(func.count(Client.id)).where(Client.active==1)) or 0
    orders_count=db.scalar(select(func.count(Order.id))) or 0
    open_orders=db.scalar(select(func.count(Order.id)).where(Order.status=="CONFIRMEE")) or 0
    stock_available=0.0
    for l in db.scalars(select(Lot).where(Lot.status=="LIBERE")).all(): stock_available += max(0,l.qty_received-l.qty_reserved-l.qty_consumed)
    production_open=db.scalar(select(func.count(ProductionJob.id)).where(ProductionJob.status!="TERMINE")) or 0
    blocked=db.scalar(select(func.count(Lot.id)).where(Lot.status=="BLOQUE")) or 0
    expiring=0; today=date.today()
    for l in db.scalars(select(Lot).where(Lot.expiry_date.is_not(None))).all():
        try:
            if (date.fromisoformat(l.expiry_date)-today).days<=3: expiring+=1
        except ValueError: pass
    order_value=sum((x.amount_ht or 0) for x in db.scalars(select(Invoice)).all())
    validated_value=sum((x.amount_ht or 0) for x in db.scalars(select(Invoice).where(Invoice.status=="VALIDEE")).all())
    b2c=db.scalar(select(func.count(Client.id)).where(Client.client_type=="B2C")) or 0
    pro=db.scalar(select(func.count(Client.id)).where(Client.client_type=="PRO")) or 0
    eq=db.scalars(select(Equipment)).all()
    return {"products":products,"clients":clients,"clients_b2c":b2c,"clients_pro":pro,"orders":orders_count,"orders_open":open_orders,"stock_available":round(stock_available,2),"production_open":production_open,"expiring_lots":expiring,"blocked_lots":blocked,"order_value_ht":round(order_value,2),"validated_value_ht":round(validated_value,2),"average_order_ht":round(order_value/orders_count,2) if orders_count else 0,"equipment_budget_low":sum(x.budget_low for x in eq),"equipment_budget_high":sum(x.budget_high for x in eq)}

@app.get("/clients")
def clients(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))): return [{"id":x.id,"client_type":x.client_type,"name":x.name,"email":x.email,"active":x.active} for x in db.scalars(select(Client).order_by(Client.name)).all()]
@app.post("/clients")
def create_client(data:ClientIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    row=Client(**data.model_dump()); db.add(row); audit(db,"CLIENT_CREATE",data.name); db.commit(); db.refresh(row); return {"id":row.id}

@app.get("/products")
def products(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for p in db.scalars(select(Product).order_by(Product.name)).all():
        cuts=[{"name":c.cut_name,"yield_rate":c.yield_rate,"extra_price_ht":c.extra_price_ht} for c in db.scalars(select(ProductCut).where(ProductCut.product_id==p.id)).all()]
        out.append({"id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"unit":p.unit,"price_ht":p.price_ht,"active":p.active,"cuts":cuts})
    return out
@app.post("/products")
def create_product(data:ProductIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if db.scalar(select(Product).where(Product.reference==data.reference)): raise HTTPException(409,"Référence déjà utilisée")
    p=Product(**data.model_dump()); db.add(p); audit(db,"PRODUCT_CREATE",data.reference); db.commit(); db.refresh(p); return {"id":p.id}

@app.delete("/products/{product_id}")
def delete_product(product_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Produit introuvable")
    has_order=db.scalar(select(func.count(OrderLine.id)).where(OrderLine.product_id==product_id)) or 0
    has_prod=db.scalar(select(func.count(ProductionJob.id)).where(ProductionJob.product_id==product_id)) or 0
    if has_order or has_prod:
        raise HTTPException(409,"Produit déjà utilisé : suppression bloquée pour préserver l'historique. Désactivez-le plutôt.")
    for cls in (ProductCut,Lot,PreparationProfile):
        for row in db.scalars(select(cls).where(cls.product_id==product_id)).all(): db.delete(row)
    audit(db,"PRODUCT_DELETE",f"product_id={product_id};reference={product.reference}")
    db.delete(product); db.commit(); return {"ok":True}


@app.get("/costing/products")
def costing_products(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for p in db.scalars(select(Product).order_by(Product.name)).all():
        c=db.scalar(select(ProductCostProfile).where(ProductCostProfile.product_id==p.id))
        purchase=c.purchase_cost_ht if c else 0.0
        packaging=c.packaging_cost_ht if c else 0.0
        labor=c.labor_cost_ht if c else 0.0
        other=c.other_cost_ht if c else 0.0
        total_cost=purchase+packaging+labor+other
        margin_value=p.price_ht-total_cost
        margin_pct=(margin_value/p.price_ht*100) if p.price_ht>0 else 0
        target=c.target_margin_pct if c else 35.0
        suggested=(total_cost/(1-target/100)) if total_cost>0 and target<100 else p.price_ht
        out.append({
            "product_id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"unit":p.unit,"price_ht":p.price_ht,
            "purchase_cost_ht":round(purchase,4),"packaging_cost_ht":round(packaging,4),"labor_cost_ht":round(labor,4),"other_cost_ht":round(other,4),
            "total_cost_ht":round(total_cost,4),"margin_value_ht":round(margin_value,4),"margin_pct":round(margin_pct,2),
            "target_margin_pct":round(target,2),"suggested_price_ht":round(suggested,2)
        })
    return out

@app.put("/costing/products/{product_id}")
def update_product_cost(product_id:int,data:ProductCostIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Produit introuvable")
    c=db.scalar(select(ProductCostProfile).where(ProductCostProfile.product_id==product_id))
    if not c:
        c=ProductCostProfile(product_id=product_id); db.add(c)
    for k,v in data.model_dump().items(): setattr(c,k,v)
    audit(db,"PRODUCT_COST_UPDATE",f"product_id={product_id};purchase={data.purchase_cost_ht};packaging={data.packaging_cost_ht};labor={data.labor_cost_ht};other={data.other_cost_ht};target={data.target_margin_pct}")
    db.commit()
    return {"ok":True}

@app.post("/products/{product_id}/price")
def update_product_price(product_id:int,data:ProductPriceUpdateIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Produit introuvable")
    old=p.price_ht
    p.price_ht=data.price_ht
    db.add(ProductPriceHistory(product_id=product_id,price_ht=data.price_ht,reason=data.reason,changed_at=datetime.now(timezone.utc).isoformat(),changed_by=user.email))
    audit(db,"PRODUCT_PRICE_UPDATE",f"product_id={product_id};old={old};new={data.price_ht};reason={data.reason}")
    db.commit()
    return {"ok":True,"old_price_ht":old,"new_price_ht":data.price_ht}

@app.get("/products/{product_id}/price-history")
def product_price_history(product_id:int,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    if not db.get(Product,product_id): raise HTTPException(404,"Produit introuvable")
    rows=db.scalars(select(ProductPriceHistory).where(ProductPriceHistory.product_id==product_id).order_by(ProductPriceHistory.id.desc())).all()
    return [{"id":x.id,"price_ht":x.price_ht,"reason":x.reason,"changed_at":x.changed_at,"changed_by":x.changed_by} for x in rows]

@app.get("/analytics/margins")
def margin_analytics(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    revenue=0.0; estimated_cost=0.0; lines_count=0
    by_product={}
    for line in db.scalars(select(OrderLine)).all():
        order=db.get(Order,line.order_id)
        if not order or order.status=="ANNULEE": continue
        amount=line.quantity*line.unit_price_ht
        c=db.scalar(select(ProductCostProfile).where(ProductCostProfile.product_id==line.product_id))
        unit_cost=(c.purchase_cost_ht+c.packaging_cost_ht+c.labor_cost_ht+c.other_cost_ht) if c else 0.0
        cost=line.quantity*unit_cost
        revenue+=amount; estimated_cost+=cost; lines_count+=1
        row=by_product.setdefault(line.product_id,{"product":line.product.name,"revenue":0.0,"cost":0.0,"qty":0.0})
        row["revenue"]+=amount; row["cost"]+=cost; row["qty"]+=line.quantity
    margin=revenue-estimated_cost
    pct=(margin/revenue*100) if revenue else 0
    ranking=[]
    for row in by_product.values():
        m=row["revenue"]-row["cost"]; mp=(m/row["revenue"]*100) if row["revenue"] else 0
        ranking.append({"product":row["product"],"revenue":round(row["revenue"],2),"estimated_cost":round(row["cost"],2),"margin":round(m,2),"margin_pct":round(mp,2),"qty":round(row["qty"],3)})
    ranking.sort(key=lambda x:x["revenue"],reverse=True)
    return {"revenue_ht":round(revenue,2),"estimated_cost_ht":round(estimated_cost,2),"estimated_margin_ht":round(margin,2),"estimated_margin_pct":round(pct,2),"lines_count":lines_count,"products":ranking[:20],"notice":"Les coûts et marges sont estimatifs tant que les coûts unitaires réels ne sont pas entièrement renseignés."}

@app.get("/lots")
def lots(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for x in db.scalars(select(Lot).order_by(Lot.expiry_date)).all():
        out.append({"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"internal_lot":x.internal_lot,"supplier_lot":x.supplier_lot,"qty_received":x.qty_received,"qty_reserved":x.qty_reserved,"qty_consumed":x.qty_consumed,"qty_available":round(lot_available(x),3),"lot_stage":lot_stage(db,x.id),"expiry_date":x.expiry_date,"status":x.status})
    return out
@app.post("/lots")
def create_lot(data:LotIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","STOCK"))):
    if not db.get(Product,data.product_id): raise HTTPException(404,"Produit introuvable")
    if db.scalar(select(Lot).where(Lot.internal_lot==data.internal_lot)): raise HTTPException(409,"Lot déjà existant")
    x=Lot(**data.model_dump()); db.add(x); db.flush(); set_lot_stage(db,x.id,"RAW","MANUAL_RECEIPT"); audit(db,"LOT_RECEIPT",data.internal_lot); db.commit(); db.refresh(x); return {"id":x.id,"lot_stage":"RAW"}

@app.get("/stock/stages")
def stock_stages(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out={"RAW":{"lots":0,"received":0.0,"reserved":0.0,"consumed":0.0,"available":0.0},"PREPARED":{"lots":0,"received":0.0,"reserved":0.0,"consumed":0.0,"available":0.0}}
    for lot in db.scalars(select(Lot)).all():
        stage=lot_stage(db,lot.id)
        if stage not in out: continue
        out[stage]["lots"]+=1
        out[stage]["received"]+=lot.qty_received
        out[stage]["reserved"]+=lot.qty_reserved
        out[stage]["consumed"]+=lot.qty_consumed
        out[stage]["available"]+=lot_available(lot)
    for stage in out:
        for key in ("received","reserved","consumed","available"):
            out[stage][key]=round(out[stage][key],3)
    return out

@app.get("/orders/{order_id}/allocations")
def order_allocations(order_id:int,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    order=db.get(Order,order_id)
    if not order: raise HTTPException(404,"Commande introuvable")
    rows=[]
    for r in db.scalars(select(Reservation).where(Reservation.order_id==order.id).order_by(Reservation.id)).all():
        lot=db.get(Lot,r.lot_id)
        rows.append({"reservation_id":r.id,"lot_id":r.lot_id,"internal_lot":lot.internal_lot if lot else None,"lot_stage":lot_stage(db,lot.id) if lot else None,"quantity":r.quantity,"status":r.status})
    jobs=[{"id":j.id,"product_name":j.product.name,"quantity_needed":j.quantity_needed,"status":j.status} for j in db.scalars(select(ProductionJob).where(ProductionJob.source_order_id==order.id)).all()]
    procurement=[{"id":p.id,"product_name":p.product.name,"requested_qty":p.requested_qty,"status":p.status} for p in db.scalars(select(ProcurementRequest).where(ProcurementRequest.source_order_id==order.id)).all()]
    return {"order_id":order.id,"order_status":order.status,"reservations":rows,"production_jobs":jobs,"procurement":procurement}

@app.get("/orders")
def orders(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for o in db.scalars(select(Order).order_by(Order.id.desc())).all():
        lines=[]; total=0.0
        for l in db.scalars(select(OrderLine).where(OrderLine.order_id==o.id)).all():
            det=db.scalar(select(ProOrderLineDetail).where(ProOrderLineDetail.order_line_id==l.id))
            amt=l.quantity*l.unit_price_ht; total+=amt
            lines.append({"id":l.id,"product_id":l.product_id,"product_name":l.product.name,"quantity":l.quantity,"unit_price_ht":l.unit_price_ht,"amount_ht":round(amt,2),"cut_name":det.cut_name if det else None,"pack_size_kg":det.pack_size_kg if det else None})
        opt=db.scalar(select(OrderOption).where(OrderOption.order_id==o.id))
        out.append({"id":o.id,"client_id":o.client_id,"client_name":o.client.name,"client_type":o.client.client_type,"status":o.status,"delivery_mode":o.delivery_mode,"created_at":o.created_at,"amount_ht":round(total,2),"note":opt.note if opt else None,"lines":lines,"product_name":lines[0]["product_name"] if lines else "—","quantity":sum(x["quantity"] for x in lines),"cut_name":lines[0]["cut_name"] if len(lines)==1 else None})
    return out

@app.post("/orders")
def create_order(data:OrderIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    client=db.get(Client,data.client_id); product=db.get(Product,data.product_id)
    if not client or not product: raise HTTPException(404,"Client ou produit introuvable")
    extra=0.0
    if data.cut_name:
        cut=db.scalar(select(ProductCut).where(ProductCut.product_id==product.id,ProductCut.cut_name==data.cut_name))
        if not cut: raise HTTPException(400,"Découpe non autorisée pour ce produit")
        extra=cut.extra_price_ht
    order=Order(client_id=client.id,status="CONFIRMEE",delivery_mode=data.delivery_mode,created_at=datetime.now(timezone.utc).isoformat()); db.add(order); db.flush()
    db.add(OrderLine(order_id=order.id,product_id=product.id,quantity=data.quantity,unit_price_ht=product.price_ht+extra)); db.add(OrderOption(order_id=order.id,cut_name=data.cut_name,note=data.note))
    remaining=reserve_order_from_lots(db,order,product,data.quantity,cut_name=data.cut_name)
    if remaining>0:
        db.add(ProductionJob(product_id=product.id,quantity_needed=remaining,status="A_PLANIFIER",source_order_id=order.id,created_at=datetime.now(timezone.utc).isoformat()))
        order.status="A_PRODUIRE"
    db.add(Delivery(order_id=order.id,status="A_PREPARER",slot=None)); amount=(product.price_ht+extra)*data.quantity; db.add(Invoice(order_id=order.id,status="BROUILLON",amount_ht=amount))
    audit(db,"ORDER_CREATE",f"order_id={order.id};product={product.reference};qty={data.quantity};cut={data.cut_name or '-'}"); db.commit()
    return {"order_id":order.id,"status":order.status,"uncovered_qty":round(remaining,3)}

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    o=db.get(Order,order_id)
    if not o: raise HTTPException(404,"Commande introuvable")
    if o.status=="ANNULEE": return {"status":"ANNULEE","released_qty":0,"warnings":[]}
    result=cancel_order_resources(db,o)
    audit(db,"ORDER_CANCEL",f"order_id={order_id};released={result['released_qty']};jobs={result['cancelled_jobs']};procurement={result['cancelled_procurement']};warnings={len(result['warnings'])}")
    db.commit()
    return {"status":o.status,**result}


def b2c_client_for_user(db:Session,user:User):
    if user.role!="CUSTOMER": raise HTTPException(403,"Compte particulier requis")
    link=db.scalar(select(B2CUserLink).where(B2CUserLink.user_id==user.id))
    if not link: raise HTTPException(404,"Profil client introuvable")
    return link.client


def reconcile_procurement_receipt(db:Session,purchase_order_line_id:int,received_delta:float):
    remaining=max(0,float(received_delta or 0))
    if remaining<=0: return []
    links=db.scalars(
        select(ProcurementPurchaseLink)
        .where(ProcurementPurchaseLink.purchase_order_line_id==purchase_order_line_id)
        .order_by(ProcurementPurchaseLink.id.asc())
    ).all()
    touched=[]
    for link in links:
        outstanding=max(0,link.allocated_qty-link.fulfilled_qty)
        if outstanding<=0: continue
        take=min(remaining,outstanding)
        link.fulfilled_qty += take
        remaining -= take
        req=db.get(ProcurementRequest,link.procurement_request_id)
        if req:
            total_alloc=db.scalar(select(func.coalesce(func.sum(ProcurementPurchaseLink.allocated_qty),0)).where(ProcurementPurchaseLink.procurement_request_id==req.id)) or 0
            total_fulfilled=db.scalar(select(func.coalesce(func.sum(ProcurementPurchaseLink.fulfilled_qty),0)).where(ProcurementPurchaseLink.procurement_request_id==req.id)) or 0
            # Current in-memory increment is not necessarily visible to aggregate before flush.
            db.flush()
            total_fulfilled=db.scalar(select(func.coalesce(func.sum(ProcurementPurchaseLink.fulfilled_qty),0)).where(ProcurementPurchaseLink.procurement_request_id==req.id)) or 0
            req.status="COUVERT" if total_alloc>0 and total_fulfilled>=total_alloc-1e-9 else "EN_COURS"
            touched.append({"request_id":req.id,"fulfilled_qty":round(float(total_fulfilled),3),"allocated_qty":round(float(total_alloc),3),"status":req.status})
        if remaining<=1e-9: break
    return touched

def available_stock_for_product(db:Session,product_id:int):
    total=0.0
    for lot in db.scalars(select(Lot).where(Lot.product_id==product_id,Lot.status=="LIBERE")).all():
        total += max(0,lot.qty_received-lot.qty_reserved-lot.qty_consumed)
    return round(total,3)

def create_procurement_need(db:Session,product:Product,qty:float,source_type:str,source_order_id:Optional[int]=None,client_id:Optional[int]=None,note:str=""):
    if qty<=0: return None
    row=ProcurementRequest(product_id=product.id,requested_qty=round(qty,3),source_type=source_type,source_order_id=source_order_id,client_id=client_id,status="A_APPROVISIONNER",note=note,created_at=datetime.now(timezone.utc).isoformat())
    db.add(row)
    return row

def reserve_b2c_line(db:Session,order:Order,product:Product,quantity:float,cut_name:Optional[str]=None):
    remaining=reserve_order_from_lots(db,order,product,quantity,cut_name=cut_name)
    if remaining>0:
        db.add(ProductionJob(product_id=product.id,quantity_needed=remaining,status="A_PLANIFIER",source_order_id=order.id,created_at=datetime.now(timezone.utc).isoformat()))
    return remaining

@app.get("/b2c/me")
def b2c_me(db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    profile=db.scalar(select(B2CProfile).where(B2CProfile.client_id==client.id))
    subs=db.scalars(select(B2CSubscription).where(B2CSubscription.client_id==client.id).order_by(B2CSubscription.id.desc())).all()
    favorites=db.scalars(select(B2CFavorite).where(B2CFavorite.client_id==client.id)).all()
    orders=db.scalars(select(Order).where(Order.client_id==client.id).order_by(Order.id.desc())).all()
    return {
        "client":{"id":client.id,"name":client.name,"email":client.email},
        "profile":{
            "household_size": profile.household_size if profile else 2,
            "weekly_budget": profile.weekly_budget if profile else 45,
            "goals": profile.goals if profile else "",
            "disliked_foods": profile.disliked_foods if profile else "",
            "declared_allergies": profile.declared_allergies if profile else "",
            "favorite_pickup_slot": profile.favorite_pickup_slot if profile else "",
            "preferred_mode": profile.preferred_mode if profile else "CLICK_COLLECT",
            "loyalty_points": profile.loyalty_points if profile else 0
        },
        "subscriptions":[{"id":s.id,"name":s.name,"frequency":s.frequency,"budget":s.budget,"pickup_day":s.pickup_day,"active":s.active} for s in subs],
        "favorites":[{"id":f.id,"product_id":f.product_id,"product_name":f.product.name,"price_ht":f.product.price_ht} for f in favorites],
        "orders":[{"id":o.id,"status":o.status,"delivery_mode":o.delivery_mode,"created_at":o.created_at} for o in orders[:10]]
    }

@app.put("/b2c/profile")
def b2c_profile_update(data:B2CProfileIn,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    profile=db.scalar(select(B2CProfile).where(B2CProfile.client_id==client.id))
    if not profile:
        profile=B2CProfile(client_id=client.id); db.add(profile)
    for k,v in data.model_dump().items(): setattr(profile,k,v)
    audit(db,"B2C_PROFILE_UPDATE",f"client_id={client.id}")
    db.commit()
    return {"ok":True}

@app.post("/b2c/favorites/{product_id}")
def b2c_favorite_toggle(product_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Produit introuvable")
    existing=db.scalar(select(B2CFavorite).where(B2CFavorite.client_id==client.id,B2CFavorite.product_id==product_id))
    if existing:
        db.delete(existing); action="removed"
    else:
        db.add(B2CFavorite(client_id=client.id,product_id=product_id)); action="added"
    audit(db,"B2C_FAVORITE",f"client_id={client.id};product_id={product_id};action={action}")
    db.commit()
    return {"ok":True,"action":action}

@app.post("/b2c/subscriptions")
def b2c_subscription_create(data:B2CSubscriptionIn,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    s=B2CSubscription(client_id=client.id,**data.model_dump(),active=1)
    db.add(s); audit(db,"B2C_SUBSCRIPTION_CREATE",f"client_id={client.id};name={s.name}"); db.commit(); db.refresh(s)
    return {"id":s.id,"ok":True}

@app.post("/b2c/subscriptions/{subscription_id}/toggle")
def b2c_subscription_toggle(subscription_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    s=db.get(B2CSubscription,subscription_id)
    if not s or s.client_id!=client.id: raise HTTPException(404,"Abonnement introuvable")
    s.active=0 if s.active else 1
    db.commit()
    return {"ok":True,"active":s.active}


def _stripe_urls():
    base=(SITE_URL or "").rstrip("/")
    success=STRIPE_SUCCESS_URL or (f"{base}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}" if base else "")
    cancel=STRIPE_CANCEL_URL or (f"{base}/?payment=cancel" if base else "")
    if not success or not cancel:
        raise HTTPException(503,"SITE_URL ou URLs Stripe non configurées")
    return success,cancel

def _order_total_ttc(db:Session,order_id:int)->float:
    total=0.0
    lines=db.scalars(select(OrderLine).where(OrderLine.order_id==order_id)).all()
    if not lines:
        raise HTTPException(409,"Commande sans ligne")
    for line in lines:
        tax=db.scalar(select(ProductTaxProfile).where(ProductTaxProfile.product_id==line.product_id))
        if not tax or tax.tax_label=="À configurer":
            raise HTTPException(409,f"TVA à configurer avant paiement en ligne pour {line.product.name}")
        total += line.quantity*line.unit_price_ht*(1+(tax.tax_rate_pct/100.0))
    return round(total,2)

def _release_unpaid_order(db:Session,order:Order):
    for r in db.scalars(select(Reservation).where(Reservation.order_id==order.id,Reservation.status=="ACTIVE")).all():
        lot=db.get(Lot,r.lot_id)
        if lot:
            lot.qty_reserved=max(0,lot.qty_reserved-r.quantity)
        r.status="ANNULEE"
    delivery=db.scalar(select(Delivery).where(Delivery.order_id==order.id))
    if delivery:
        delivery.status="ANNULEE"
    for req in db.scalars(select(ProcurementRequest).where(ProcurementRequest.source_order_id==order.id,ProcurementRequest.status.in_(["A_APPROVISIONNER","EN_COURS"]))).all():
        req.status="ANNULE"
    order.status="ANNULEE"

@app.post("/b2c/checkout")
def b2c_checkout(data:B2CCheckoutIn,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    if not data.lines: raise HTTPException(400,"Panier vide")
    payment_method=(data.payment_method or "SUR_PLACE").upper()
    if payment_method not in ("SUR_PLACE","CLICK_COLLECT","STRIPE"):
        raise HTTPException(400,"Mode de paiement non autorisé")
    if payment_method=="STRIPE" and not (STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET):
        raise HTTPException(503,"Paiement en ligne temporairement indisponible")
    order=Order(client_id=client.id,status="CONFIRMEE",delivery_mode=data.delivery_mode,created_at=datetime.now(timezone.utc).isoformat())
    db.add(order); db.flush()
    total=0.0; uncovered_total=0.0
    first_cut=None
    for line in data.lines:
        product=db.get(Product,line.product_id)
        if not product or not product.active: raise HTTPException(404,"Produit indisponible")
        extra=0.0
        if line.cut_name:
            cut=db.scalar(select(ProductCut).where(ProductCut.product_id==product.id,ProductCut.cut_name==line.cut_name))
            if not cut: raise HTTPException(400,f"Découpe non autorisée pour {product.name}")
            extra=cut.extra_price_ht
        unit_price=product.price_ht+extra
        ol=OrderLine(order_id=order.id,product_id=product.id,quantity=line.quantity,unit_price_ht=unit_price)
        db.add(ol)
        total += unit_price*line.quantity
        uncovered=reserve_b2c_line(db,order,product,line.quantity,line.cut_name)
        uncovered_total += uncovered
        if uncovered>0:
            create_procurement_need(db,product,uncovered,"B2C_ORDER",order.id,client.id,"Stock insuffisant : approvisionnement fournisseur requis.")
        if first_cut is None: first_cut=line.cut_name
    post_payment_status="A_PRODUIRE" if uncovered_total>0 else "CONFIRMEE"
    order.status=post_payment_status
    db.add(OrderOption(order_id=order.id,cut_name=first_cut,note=data.note))
    db.add(Delivery(order_id=order.id,status="A_PREPARER" if payment_method!="STRIPE" else "PAIEMENT_EN_ATTENTE",slot=data.slot))
    db.add(Invoice(order_id=order.id,status="BROUILLON",amount_ht=round(total,2)))
    pay_status="A_PAYER" if payment_method in ("SUR_PLACE","CLICK_COLLECT") else "EN_ATTENTE"
    payment=Payment(order_id=order.id,status=pay_status,method=payment_method,amount=round(total,2),reference=None)
    db.add(payment)
    audit(db,"B2C_CHECKOUT",f"order_id={order.id};client_id={client.id};lines={len(data.lines)};amount={round(total,2)};mode={data.delivery_mode};payment={payment_method}")
    if payment_method=="STRIPE":
        amount_ttc=_order_total_ttc(db,order.id)
        order.status="PAIEMENT_EN_ATTENTE"
        success_url,cancel_url=_stripe_urls()
        try:
            session=stripe.checkout.Session.create(
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(order.id),
                customer_email=client.email or None,
                line_items=[{
                    "price_data":{
                        "currency":STRIPE_CURRENCY,
                        "product_data":{"name":f"Commande Le Panier Frais Bio #{order.id}"},
                        "unit_amount":int(round(amount_ttc*100)),
                    },
                    "quantity":1,
                }],
                metadata={"order_id":str(order.id),"client_id":str(client.id),"post_payment_status":post_payment_status},
                payment_intent_data={"metadata":{"order_id":str(order.id)}},
            )
        except Exception as exc:
            _release_unpaid_order(db,order)
            payment.status="ECHEC_CREATION"
            audit(db,"STRIPE_SESSION_ERROR",f"order_id={order.id};type={type(exc).__name__}")
            db.commit()
            raise HTTPException(502,"Impossible d'initialiser le paiement sécurisé")
        payment.amount=amount_ttc
        payment.reference=session.id
        db.commit()
        return {"order_id":order.id,"status":order.status,"amount":amount_ttc,"payment_status":pay_status,"slot":data.slot,"checkout_url":session.url}
    db.commit()
    return {"order_id":order.id,"status":order.status,"amount":round(total,2),"payment_status":pay_status,"slot":data.slot}

@app.get("/b2c/orders/{order_id}")
def b2c_order_detail(order_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    order=db.get(Order,order_id)
    if not order or order.client_id!=client.id: raise HTTPException(404,"Commande introuvable")
    lines=[]
    for l in db.scalars(select(OrderLine).where(OrderLine.order_id==order.id)).all():
        lines.append({"product_id":l.product_id,"product_name":l.product.name,"quantity":l.quantity,"unit_price_ht":l.unit_price_ht,"amount_ht":round(l.quantity*l.unit_price_ht,2)})
    delivery=db.scalar(select(Delivery).where(Delivery.order_id==order.id))
    payment=db.scalar(select(Payment).where(Payment.order_id==order.id))
    invoice=db.scalar(select(Invoice).where(Invoice.order_id==order.id))
    return {"id":order.id,"status":order.status,"delivery_mode":order.delivery_mode,"created_at":order.created_at,"slot":delivery.slot if delivery else None,"delivery_status":delivery.status if delivery else None,"payment":{"status":payment.status,"method":payment.method,"amount":payment.amount} if payment else None,"invoice_status":invoice.status if invoice else None,"lines":lines}

@app.post("/b2c/orders/{order_id}/cancel")
def b2c_cancel_order(order_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    client=b2c_client_for_user(db,user)
    order=db.get(Order,order_id)
    if not order or order.client_id!=client.id: raise HTTPException(404,"Commande introuvable")
    if order.status in ("LIVREE","ANNULEE"): raise HTTPException(409,"Commande non annulable")
    for r in db.scalars(select(Reservation).where(Reservation.order_id==order.id,Reservation.status=="ACTIVE")).all():
        lot=db.get(Lot,r.lot_id)
        if lot: lot.qty_reserved=max(0,lot.qty_reserved-r.quantity)
        r.status="ANNULEE"
    for j in db.scalars(select(ProductionJob).where(ProductionJob.source_order_id==order.id)).all():
        if j.status!="TERMINE": j.status="ANNULE"
    delivery=db.scalar(select(Delivery).where(Delivery.order_id==order.id))
    if delivery: delivery.status="ANNULEE"
    payment=db.scalar(select(Payment).where(Payment.order_id==order.id))
    if payment and payment.status!="PAYE": payment.status="ANNULE"
    order.status="ANNULEE"
    audit(db,"B2C_ORDER_CANCEL",f"order_id={order.id};client_id={client.id}")
    db.commit()
    return {"ok":True}

@app.get("/pro/profile")
def pro_profile(db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role!="PRO": raise HTTPException(403,"Compte professionnel requis")
    client=pro_client_for_user(db,user)
    if not client: raise HTTPException(404,"Compte client PRO non relié")
    profile=db.scalar(select(ProRestaurantProfile).where(ProRestaurantProfile.client_id==client.id))
    if not profile:
        profile=ProRestaurantProfile(client_id=client.id); db.add(profile); db.commit(); db.refresh(profile)
    return {"client_id":client.id,"restaurant":client.name,"covers_lunch":profile.covers_lunch,"covers_dinner":profile.covers_dinner,"delivery_days":profile.delivery_days,"default_pack_kg":profile.default_pack_kg,"prep_hour_cost":profile.prep_hour_cost,"prep_minutes_per_kg":profile.prep_minutes_per_kg,"notes":profile.notes}

@app.put("/pro/profile")
def update_pro_profile(data:ProProfileIn,db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role!="PRO": raise HTTPException(403,"Compte professionnel requis")
    client=pro_client_for_user(db,user)
    if not client: raise HTTPException(404,"Compte client PRO non relié")
    profile=db.scalar(select(ProRestaurantProfile).where(ProRestaurantProfile.client_id==client.id))
    if not profile:
        profile=ProRestaurantProfile(client_id=client.id); db.add(profile)
    for k,v in data.model_dump().items(): setattr(profile,k,v)
    audit(db,"PRO_PROFILE_UPDATE",f"client={client.name}")
    db.commit(); return {"ok":True}

@app.post("/pro/service-calculator")
def pro_service_calculator(data:ProServiceCalcIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE","PRO"))):
    p=db.get(Product,data.product_id)
    if not p: raise HTTPException(404,"Produit introuvable")
    cut=db.scalar(select(ProductCut).where(ProductCut.product_id==p.id,ProductCut.cut_name==data.cut_name)) if data.cut_name else None
    prep=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==p.id,PreparationProfile.cut_name==data.cut_name)) if data.cut_name else None
    yield_rate=(prep.yield_rate if prep else (cut.yield_rate if cut else .88)) or .88
    net_kg=data.covers*data.grams_per_cover/1000
    gross_kg=net_kg/max(yield_rate,.01)
    packs=max(1,__import__('math').ceil(net_kg/data.pack_size_kg))
    unit_price=p.price_ht+(cut.extra_price_ht if cut else 0)
    amount_ht=net_kg*unit_price
    # Simulation values are profile parameters and remain editable by the restaurant.
    mins_per_kg=12.0; hour_cost=20.0
    if user.role=="PRO":
        client=pro_client_for_user(db,user)
        profile=db.scalar(select(ProRestaurantProfile).where(ProRestaurantProfile.client_id==client.id)) if client else None
        if profile:
            mins_per_kg=profile.prep_minutes_per_kg; hour_cost=profile.prep_hour_cost
    saved_minutes=net_kg*mins_per_kg
    labor_value=saved_minutes/60*hour_cost
    return {"product_id":p.id,"product_name":p.name,"cut_name":data.cut_name or "Standard","covers":data.covers,"grams_per_cover":data.grams_per_cover,"net_kg":round(net_kg,2),"gross_kg_estimated":round(gross_kg,2),"yield_rate":round(yield_rate,3),"pack_size_kg":data.pack_size_kg,"packs":packs,"amount_ht_estimated":round(amount_ht,2),"prep_minutes_saved_simulation":round(saved_minutes),"labor_value_simulation":round(labor_value,2),"simulation_note":"Temps et valeur de main-d’œuvre calculés avec les paramètres du profil restaurant ; à adapter à l’organisation réelle."}

@app.get("/today")
def today_board(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    open_orders=db.scalars(select(Order).where(Order.status!="ANNULEE").order_by(Order.id.desc())).all()
    jobs=db.scalars(select(ProductionJob).where(ProductionJob.status!="TERMINE").order_by(ProductionJob.id)).all()
    dels=db.scalars(select(Delivery).where(Delivery.status.not_in(["LIVREE","RETIRÉE"])).order_by(Delivery.id)).all()
    by_product={}
    for j in jobs:
        by_product.setdefault(j.product.name,0.0); by_product[j.product.name]+=j.quantity_needed
    return {"orders_open":len(open_orders),"production_open":len(jobs),"deliveries_open":len(dels),"production_by_product":[{"product":k,"quantity":round(v,2)} for k,v in sorted(by_product.items(),key=lambda x:-x[1])[:10]],"next_actions":[
        {"time":"08:30","label":"Réception & contrôle fournisseurs","type":"RECEPTION"},
        {"time":"09:00","label":f"Préparer {len(jobs)} besoins de production","type":"PRODUCTION"},
        {"time":"11:30","label":"Contrôle qualité & emballage","type":"QUALITE"},
        {"time":"13:00","label":f"Organiser {len(dels)} retraits / livraisons","type":"LIVRAISON"}
    ]}

@app.get("/pro/me")
def pro_me(db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role!="PRO": raise HTTPException(403,"Compte professionnel requis")
    client=pro_client_for_user(db,user)
    if not client: raise HTTPException(404,"Compte client PRO non relié")
    orders=db.scalars(select(Order).where(Order.client_id==client.id).order_by(Order.id.desc())).all()
    return {"client_id":client.id,"name":client.name,"email":client.email,"orders_count":len(orders),"last_order_id":orders[0].id if orders else None}

@app.post("/pro/orders/batch")
def create_pro_batch(data:ProBatchOrderIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE","PRO"))):
    client=db.get(Client,data.client_id)
    if not client or client.client_type!="PRO": raise HTTPException(400,"Client professionnel requis")
    if user.role=="PRO":
        own=pro_client_for_user(db,user)
        if not own or own.id!=client.id: raise HTTPException(403,"Vous ne pouvez commander que pour votre établissement")
    if not data.lines: raise HTTPException(400,"Commande vide")
    order=Order(client_id=client.id,status="CONFIRMEE",delivery_mode=data.delivery_mode,created_at=datetime.now(timezone.utc).isoformat())
    db.add(order); db.flush(); total=0.0
    for item in data.lines:
        p=db.get(Product,item.product_id)
        if not p: raise HTTPException(404,f"Produit {item.product_id} introuvable")
        cut=db.scalar(select(ProductCut).where(ProductCut.product_id==p.id,ProductCut.cut_name==item.cut_name)) if item.cut_name else None
        unit_price=p.price_ht+(cut.extra_price_ht if cut else 0)
        line=OrderLine(order_id=order.id,product_id=p.id,quantity=item.quantity_kg,unit_price_ht=unit_price)
        db.add(line); db.flush(); total += item.quantity_kg*unit_price
        db.add(ProOrderLineDetail(order_line_id=line.id,cut_name=item.cut_name,pack_size_kg=item.pack_size_kg,note=item.note))
        available=available_stock_for_product(db,p.id)
        missing=max(0,item.quantity_kg-available)
        if missing>0:
            create_procurement_need(db,p,missing,"PRO_ORDER",order.id,client.id,"Approvisionnement nécessaire pour commande PRO.")
        db.add(ProductionJob(product_id=p.id,quantity_needed=item.quantity_kg,status="A_PLANIFIER",source_order_id=order.id,created_at=datetime.now(timezone.utc).isoformat()))
    db.add(OrderOption(order_id=order.id,note=data.note))
    db.add(Delivery(order_id=order.id,status="A_PREPARER"))
    db.add(Invoice(order_id=order.id,status="BROUILLON",amount_ht=total))
    audit(db,"PRO_BATCH_ORDER_CREATE",f"order_id={order.id};client={client.name};lines={len(data.lines)};total_ht={total:.2f}")
    db.commit(); db.refresh(order)
    return {"order_id":order.id,"status":order.status,"amount_ht":round(total,2),"lines":len(data.lines)}

@app.get("/pro/templates")
def pro_templates(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    stmt=select(ProOrderTemplate).where(ProOrderTemplate.active==1)
    if user.role=="PRO":
        own=pro_client_for_user(db,user)
        if not own: raise HTTPException(404,"Compte client PRO non relié")
        stmt=stmt.where(ProOrderTemplate.client_id==own.id)
    for t in db.scalars(stmt.order_by(ProOrderTemplate.name)).all():
        lines=[]
        for l in db.scalars(select(ProOrderTemplateLine).where(ProOrderTemplateLine.template_id==t.id)).all():
            lines.append({"product_id":l.product_id,"product_name":l.product.name,"quantity_kg":l.quantity_kg,"cut_name":l.cut_name,"pack_size_kg":l.pack_size_kg})
        out.append({"id":t.id,"client_id":t.client_id,"client_name":t.client.name,"name":t.name,"delivery_mode":t.delivery_mode,"lines":lines})
    return out

@app.post("/pro/templates")
def create_pro_template(data:ProTemplateIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE","PRO"))):
    client=db.get(Client,data.client_id)
    if not client or client.client_type!="PRO": raise HTTPException(400,"Client professionnel requis")
    if user.role=="PRO":
        own=pro_client_for_user(db,user)
        if not own or own.id!=client.id: raise HTTPException(403,"Établissement non autorisé")
    t=ProOrderTemplate(client_id=client.id,name=data.name,delivery_mode=data.delivery_mode,active=1); db.add(t); db.flush()
    for item in data.lines:
        if not db.get(Product,item.product_id): raise HTTPException(404,"Produit introuvable")
        db.add(ProOrderTemplateLine(template_id=t.id,product_id=item.product_id,quantity_kg=item.quantity_kg,cut_name=item.cut_name,pack_size_kg=item.pack_size_kg or 2.5))
    audit(db,"PRO_TEMPLATE_CREATE",f"template={data.name};client={client.name};lines={len(data.lines)}"); db.commit(); db.refresh(t); return {"id":t.id}

@app.post("/pro/templates/{template_id}/order")
def order_from_template(template_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE","PRO"))):
    t=db.get(ProOrderTemplate,template_id)
    if not t: raise HTTPException(404,"Modèle introuvable")
    if user.role=="PRO":
        own=pro_client_for_user(db,user)
        if not own or own.id!=t.client_id: raise HTTPException(403,"Modèle non autorisé")
    lines=db.scalars(select(ProOrderTemplateLine).where(ProOrderTemplateLine.template_id==t.id)).all()
    payload=ProBatchOrderIn(client_id=t.client_id,delivery_mode=t.delivery_mode,lines=[ProBatchLineIn(product_id=l.product_id,quantity_kg=l.quantity_kg,cut_name=l.cut_name,pack_size_kg=l.pack_size_kg) for l in lines],note=f"Commande depuis modèle : {t.name}")
    return create_pro_batch(payload,db,user)


@app.get("/production/batches")
def production_batches(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for b in db.scalars(select(ProductionBatch).order_by(ProductionBatch.id.desc())).all():
        consumptions=db.scalars(select(ProductionConsumption).where(ProductionConsumption.batch_id==b.id)).all()
        out.append({
            "id":b.id,"job_id":b.job_id,"product_name":b.job.product.name,"cut_name":b.cut_name,"packaging":b.packaging,
            "actual_input_qty":b.actual_input_qty,"actual_output_qty":b.actual_output_qty,"temperature_c":b.temperature_c,
            "quality_status":b.quality_status,"operator_notes":b.operator_notes,"completed_at":b.completed_at,
            "output_lot":b.output_lot.internal_lot if b.output_lot else None,
            "expiry_date":b.output_lot.expiry_date if b.output_lot else None,
            "sources":[{"lot":c.source_lot.internal_lot,"supplier_lot":c.source_lot.supplier_lot,"quantity":c.quantity} for c in consumptions]
        })
    return out

@app.get("/production/{job_id}/suggest-inputs")
def production_suggest_inputs(job_id:int,input_qty:float,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    job=db.get(ProductionJob,job_id)
    if not job: raise HTTPException(404,"Production introuvable")
    if input_qty<=0: raise HTTPException(400,"Quantité invalide")
    remaining=input_qty; rows=[]
    lots=db.scalars(select(Lot).where(Lot.product_id==job.product_id,Lot.status=="LIBERE").order_by(Lot.expiry_date.asc(),Lot.id.asc())).all()
    for lot in lots:
        available=max(0,lot.qty_received-lot.qty_reserved-lot.qty_consumed)
        take=min(available,remaining)
        if take>0:
            rows.append({"lot_id":lot.id,"internal_lot":lot.internal_lot,"supplier_lot":lot.supplier_lot,"available":round(available,3),"suggested_qty":round(take,3),"expiry_date":lot.expiry_date})
            remaining-=take
        if remaining<=0: break
    return {"job_id":job.id,"product_name":job.product.name,"requested_input_qty":input_qty,"uncovered_qty":round(max(0,remaining),3),"lots":rows}

@app.post("/production/{job_id}/complete")
def production_complete(job_id:int,data:ProductionCompleteIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","PRODUCTION"))):
    job=db.get(ProductionJob,job_id)
    if not job: raise HTTPException(404,"Production introuvable")
    if job.status=="TERMINE": raise HTTPException(409,"Production déjà terminée")
    if db.scalar(select(ProductionBatch).where(ProductionBatch.job_id==job.id)):
        raise HTTPException(409,"Un lot de sortie existe déjà pour cette production")
    if db.scalar(select(Lot).where(Lot.internal_lot==data.internal_lot)):
        raise HTTPException(409,"Numéro de lot déjà utilisé")

    remaining=data.actual_input_qty
    allocations=[]

    # 1. Reprise transactionnelle des réservations RAW de la commande source, si elles existent.
    if job.source_order_id:
        reservations=db.scalars(select(Reservation).where(Reservation.order_id==job.source_order_id,Reservation.status=="ACTIVE").order_by(Reservation.id.asc())).all()
        for r in reservations:
            lot=db.get(Lot,r.lot_id)
            if not lot or lot.product_id!=job.product_id or lot.status!="LIBERE" or lot_stage(db,lot.id)!="RAW":
                continue
            reserved_take=min(remaining,r.quantity,lot.qty_reserved)
            if reserved_take<=0: continue
            lot.qty_reserved-=reserved_take
            lot.qty_consumed+=reserved_take
            r.quantity-=reserved_take
            if r.quantity<=1e-9:
                r.quantity=0; r.status="RELEASED_TO_PRODUCTION"
            allocations.append((lot,reserved_take))
            remaining-=reserved_take
            if remaining<=1e-9: break

    # 2. Complément FEFO uniquement sur lots RAW libérés et non réservés.
    if remaining>1e-9:
        lots=db.scalars(select(Lot).where(Lot.product_id==job.product_id,Lot.status=="LIBERE").order_by(Lot.expiry_date.asc(),Lot.id.asc())).all()
        for lot in lots:
            if lot_stage(db,lot.id)!="RAW": continue
            available=lot_available(lot)
            take=min(max(0,available),remaining)
            if take>0:
                lot.qty_consumed += take
                allocations.append((lot,take))
                remaining-=take
            if remaining<=1e-9: break

    if remaining>1e-9:
        db.rollback()
        raise HTTPException(409,f"Stock RAW source insuffisant : {round(remaining,3)} unité(s) non couverte(s)")

    # Contrôle défensif avant création du lot fini.
    for lot,_ in allocations:
        if lot_available(lot)<-1e-9:
            db.rollback()
            raise HTTPException(409,f"Incohérence stock sur lot {lot.internal_lot}")

    quality=data.quality_status.upper()
    if quality not in ("VALIDEE","BLOQUEE"):
        db.rollback()
        raise HTTPException(400,"Statut qualité attendu : VALIDEE ou BLOQUEE")
    output_status="LIBERE" if quality=="VALIDEE" else "BLOQUE"

    output=Lot(product_id=job.product_id,internal_lot=data.internal_lot,supplier_lot=None,qty_received=data.actual_output_qty,qty_reserved=0,qty_consumed=0,expiry_date=data.expiry_date,status=output_status)
    db.add(output); db.flush()
    set_lot_stage(db,output.id,"PREPARED","PRODUCTION_OUTPUT")

    batch=ProductionBatch(job_id=job.id,output_lot_id=output.id,cut_name=data.cut_name,packaging=data.packaging,actual_input_qty=data.actual_input_qty,actual_output_qty=data.actual_output_qty,temperature_c=data.temperature_c,quality_status=quality,operator_notes=data.operator_notes,completed_at=datetime.now(timezone.utc).isoformat())
    db.add(batch); db.flush()
    for lot,take in allocations:
        db.add(ProductionConsumption(batch_id=batch.id,source_lot_id=lot.id,quantity=take))

    reserved_output=0.0
    if job.source_order_id and output_status=="LIBERE":
        target=min(job.quantity_needed,data.actual_output_qty)
        if target>0:
            output.qty_reserved+=target
            db.add(Reservation(order_id=job.source_order_id,lot_id=output.id,quantity=target,status="ACTIVE"))
            reserved_output=target
        deficit=max(0,job.quantity_needed-target)
        if deficit>1e-9:
            db.add(ProductionJob(product_id=job.product_id,quantity_needed=deficit,status="A_PLANIFIER",source_order_id=job.source_order_id,created_at=datetime.now(timezone.utc).isoformat()))

    job.status="TERMINE"
    audit(db,"PRODUCTION_COMPLETE",f"job_id={job.id};batch_id={batch.id};output_lot={data.internal_lot};input={data.actual_input_qty};output={data.actual_output_qty};quality={quality};reserved_output={reserved_output}")
    db.commit(); db.refresh(batch)
    return {"ok":True,"batch_id":batch.id,"output_lot":data.internal_lot,"lot_status":output_status,"lot_stage":"PREPARED","quality_status":quality,"reserved_output":round(reserved_output,3)}

@app.get("/production/batches/{batch_id}/label")
def production_label(batch_id:int,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    b=db.get(ProductionBatch,batch_id)
    if not b: raise HTTPException(404,"Lot de production introuvable")
    return {
        "brand":"Le Panier Frais Bio","product":b.job.product.name,"internal_lot":b.output_lot.internal_lot if b.output_lot else None,
        "cut_name":b.cut_name,"net_quantity":b.actual_output_qty,"packaging":b.packaging,
        "expiry_date":b.output_lot.expiry_date if b.output_lot else None,"quality_status":b.quality_status,
        "completed_at":b.completed_at,
        "notice":"La date de conservation affichée est celle saisie et validée par l'opérateur ; aucune durée n'est calculée automatiquement."
    }

@app.get("/traceability/{internal_lot}")
def traceability(internal_lot:str,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    lot=db.scalar(select(Lot).where(Lot.internal_lot==internal_lot))
    if not lot: raise HTTPException(404,"Lot introuvable")
    batch=db.scalar(select(ProductionBatch).where(ProductionBatch.output_lot_id==lot.id))
    upstream=[]
    if batch:
        for c in db.scalars(select(ProductionConsumption).where(ProductionConsumption.batch_id==batch.id)).all():
            upstream.append({"internal_lot":c.source_lot.internal_lot,"supplier_lot":c.source_lot.supplier_lot,"quantity":c.quantity,"expiry_date":c.source_lot.expiry_date,"lot_stage":lot_stage(db,c.source_lot.id)})
    downstream=[]
    for r in db.scalars(select(Reservation).where(Reservation.lot_id==lot.id)).all():
        o=db.get(Order,r.order_id)
        downstream.append({"order_id":r.order_id,"client":o.client.name if o else None,"quantity":r.quantity,"reservation_status":r.status})
    return {
        "lot":{"internal_lot":lot.internal_lot,"product":lot.product.name,"supplier_lot":lot.supplier_lot,"status":lot.status,"lot_stage":lot_stage(db,lot.id),"expiry_date":lot.expiry_date,"qty_received":lot.qty_received,"qty_reserved":lot.qty_reserved,"qty_consumed":lot.qty_consumed,"qty_available":round(lot_available(lot),3)},
        "production":{"batch_id":batch.id,"job_id":batch.job_id,"cut_name":batch.cut_name,"packaging":batch.packaging,"temperature_c":batch.temperature_c,"quality_status":batch.quality_status,"completed_at":batch.completed_at} if batch else None,
        "upstream":upstream,"downstream":downstream
    }

@app.get("/production")
def production(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for x in db.scalars(select(ProductionJob).order_by(ProductionJob.id.desc())).all():
        b=db.scalar(select(ProductionBatch).where(ProductionBatch.job_id==x.id))
        out.append({"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"quantity_needed":x.quantity_needed,"status":x.status,"source_order_id":x.source_order_id,"created_at":x.created_at,"batch_id":b.id if b else None,"output_lot":b.output_lot.internal_lot if b and b.output_lot else None})
    return out
@app.post("/production")
def create_production(data:ProductionIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","PRODUCTION"))):
    if not db.get(Product,data.product_id): raise HTTPException(404,"Produit introuvable")
    x=ProductionJob(product_id=data.product_id,quantity_needed=data.quantity_needed,status="A_PLANIFIER",source_order_id=data.source_order_id,created_at=datetime.now(timezone.utc).isoformat()); db.add(x); audit(db,"PRODUCTION_CREATE",f"product_id={data.product_id};qty={data.quantity_needed}"); db.commit(); db.refresh(x); return {"id":x.id}
@app.post("/production/{job_id}/advance")
def advance_production(job_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","PRODUCTION"))):
    x=db.get(ProductionJob,job_id)
    if not x: raise HTTPException(404,"Production introuvable")
    seq=["A_PLANIFIER","EN_PREPARATION","CONTROLE_QUALITE","TERMINE"]; x.status=seq[min(seq.index(x.status)+1,len(seq)-1)] if x.status in seq else "A_PLANIFIER"; audit(db,"PRODUCTION_ADVANCE",f"job_id={job_id};status={x.status}"); db.commit(); return {"status":x.status}

@app.get("/deliveries")
def deliveries(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for d in db.scalars(select(Delivery).order_by(Delivery.id.desc())).all():
        o=db.get(Order,d.order_id); out.append({"id":d.id,"order_id":d.order_id,"client_name":o.client.name if o else "—","mode":o.delivery_mode if o else "—","status":d.status,"slot":d.slot})
    return out
@app.post("/deliveries/{delivery_id}/advance")
def advance_delivery(delivery_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","LIVRAISON"))):
    d=db.get(Delivery,delivery_id)
    if not d: raise HTTPException(404,"Livraison introuvable")
    order=db.get(Order,d.order_id)
    if not order: raise HTTPException(404,"Commande introuvable")
    if order.status=="ANNULEE": raise HTTPException(409,"Commande annulée")
    terminal="LIVREE" if order.delivery_mode=="LIVRAISON" else "RETIRÉE"
    if d.status==terminal:
        return {"status":d.status,"order_status":order.status,"consumed_qty":0}
    seq=["A_PREPARER","PRETE","EN_COURS","LIVREE"] if order.delivery_mode=="LIVRAISON" else ["A_PREPARER","PRETE","RETIRÉE"]
    d.status=seq[min(seq.index(d.status)+1,len(seq)-1)] if d.status in seq else seq[0]
    consumed=0.0
    if d.status==terminal:
        consumed=fulfill_order_reservations(db,order.id)
        order.status="TERMINEE"
    audit(db,"DELIVERY_ADVANCE",f"delivery_id={delivery_id};status={d.status};order_id={order.id};consumed={consumed}")
    db.commit()
    return {"status":d.status,"order_status":order.status,"consumed_qty":consumed}


def compute_invoice_tax_snapshot(db:Session,invoice:Invoice,replace_existing:bool=True):
    order=db.get(Order,invoice.order_id)
    if not order: raise HTTPException(404,"Commande liée introuvable")
    existing=db.scalars(select(InvoiceTaxLine).where(InvoiceTaxLine.invoice_id==invoice.id)).all()
    if replace_existing:
        for row in existing: db.delete(row)
        db.flush()
    elif existing:
        summary=db.scalar(select(InvoiceFiscalSummary).where(InvoiceFiscalSummary.invoice_id==invoice.id))
        return summary
    total_ht=0.0; total_tax=0.0
    for line in db.scalars(select(OrderLine).where(OrderLine.order_id==order.id)).all():
        profile=db.scalar(select(ProductTaxProfile).where(ProductTaxProfile.product_id==line.product_id))
        rate=profile.tax_rate_pct if profile else 0.0
        amount_ht=round(line.quantity*line.unit_price_ht,2)
        amount_tax=round(amount_ht*rate/100,2)
        amount_ttc=round(amount_ht+amount_tax,2)
        total_ht+=amount_ht; total_tax+=amount_tax
        db.add(InvoiceTaxLine(invoice_id=invoice.id,order_line_id=line.id,product_name=line.product.name,quantity=line.quantity,unit_price_ht=line.unit_price_ht,tax_rate_pct=rate,amount_ht=amount_ht,amount_tax=amount_tax,amount_ttc=amount_ttc))
    total_ht=round(total_ht,2); total_tax=round(total_tax,2); total_ttc=round(total_ht+total_tax,2)
    summary=db.scalar(select(InvoiceFiscalSummary).where(InvoiceFiscalSummary.invoice_id==invoice.id))
    if not summary:
        summary=InvoiceFiscalSummary(invoice_id=invoice.id,amount_ht=total_ht,amount_tax=total_tax,amount_ttc=total_ttc)
        db.add(summary)
    else:
        summary.amount_ht=total_ht; summary.amount_tax=total_tax; summary.amount_ttc=total_ttc
    invoice.amount_ht=total_ht
    return summary

@app.get("/tax/products")
def product_tax_profiles(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for p in db.scalars(select(Product).order_by(Product.name)).all():
        t=db.scalar(select(ProductTaxProfile).where(ProductTaxProfile.product_id==p.id))
        out.append({"product_id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"tax_rate_pct":t.tax_rate_pct if t else 0.0,"tax_label":t.tax_label if t else "À configurer","configured":bool(t)})
    return out

@app.put("/tax/products/{product_id}")
def update_product_tax(product_id:int,data:ProductTaxIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Produit introuvable")
    row=db.scalar(select(ProductTaxProfile).where(ProductTaxProfile.product_id==product_id))
    if not row:
        row=ProductTaxProfile(product_id=product_id); db.add(row)
    row.tax_rate_pct=data.tax_rate_pct; row.tax_label=data.tax_label
    audit(db,"PRODUCT_TAX_UPDATE",f"product_id={product_id};rate={data.tax_rate_pct};label={data.tax_label}")
    db.commit(); return {"ok":True}

@app.post("/invoices/{invoice_id}/preview-tax")
def preview_invoice_tax(invoice_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    invoice=db.get(Invoice,invoice_id)
    if not invoice: raise HTTPException(404,"Facture introuvable")
    if invoice.status=="VALIDEE": raise HTTPException(409,"Facture validée : aperçu fiscal figé")
    summary=compute_invoice_tax_snapshot(db,invoice,replace_existing=True)
    db.commit()
    return {"invoice_id":invoice.id,"amount_ht":summary.amount_ht,"amount_tax":summary.amount_tax,"amount_ttc":summary.amount_ttc}

@app.post("/invoices/{invoice_id}/finalize")
def finalize_invoice(invoice_id:int,data:InvoiceFinalizeIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    invoice=db.get(Invoice,invoice_id)
    if not invoice: raise HTTPException(404,"Facture introuvable")
    summary=compute_invoice_tax_snapshot(db,invoice,replace_existing=invoice.status!="VALIDEE")
    if invoice.status!="VALIDEE":
        now=datetime.now(timezone.utc)
        number=f"LPFB-{now.year}-{invoice.id:06d}"
        summary.invoice_number=number
        summary.issued_at=now.isoformat()
        summary.due_date=data.due_date
        invoice.status="VALIDEE"
        audit(db,"INVOICE_FINALIZE",f"invoice_id={invoice.id};number={number};ht={summary.amount_ht};tax={summary.amount_tax};ttc={summary.amount_ttc}")
    db.commit()
    return {"invoice_id":invoice.id,"invoice_number":summary.invoice_number,"amount_ht":summary.amount_ht,"amount_tax":summary.amount_tax,"amount_ttc":summary.amount_ttc,"status":invoice.status}

@app.get("/invoices/{invoice_id}/detail")
def invoice_detail(invoice_id:int,db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    invoice=db.get(Invoice,invoice_id)
    if not invoice: raise HTTPException(404,"Facture introuvable")
    order=db.get(Order,invoice.order_id)
    summary=db.scalar(select(InvoiceFiscalSummary).where(InvoiceFiscalSummary.invoice_id==invoice.id))
    lines=db.scalars(select(InvoiceTaxLine).where(InvoiceTaxLine.invoice_id==invoice.id)).all()
    payment=db.scalar(select(Payment).where(Payment.order_id==invoice.order_id))
    credits=db.scalars(select(CreditNote).where(CreditNote.invoice_id==invoice.id).order_by(CreditNote.id.desc())).all()
    return {
        "id":invoice.id,"order_id":invoice.order_id,"client_name":order.client.name if order else "—","status":invoice.status,
        "invoice_number":summary.invoice_number if summary else None,"issued_at":summary.issued_at if summary else None,"due_date":summary.due_date if summary else None,
        "amount_ht":summary.amount_ht if summary else invoice.amount_ht,"amount_tax":summary.amount_tax if summary else None,"amount_ttc":summary.amount_ttc if summary else None,
        "lines":[{"product_name":x.product_name,"quantity":x.quantity,"unit_price_ht":x.unit_price_ht,"tax_rate_pct":x.tax_rate_pct,"amount_ht":x.amount_ht,"amount_tax":x.amount_tax,"amount_ttc":x.amount_ttc} for x in lines],
        "payment":{"status":payment.status,"method":payment.method,"amount":payment.amount,"reference":payment.reference} if payment else None,
        "credits":[{"id":c.id,"credit_number":c.credit_number,"reason":c.reason,"amount_ht":c.amount_ht,"amount_tax":c.amount_tax,"amount_ttc":c.amount_ttc,"created_at":c.created_at,"status":c.status} for c in credits]
    }

@app.post("/payments/stripe/webhook")
async def stripe_webhook(request:Request,db:Session=Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503,"Webhook Stripe non configuré")
    payload=await request.body()
    signature=request.headers.get("stripe-signature","")
    try:
        event=stripe.Webhook.construct_event(payload,signature,STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400,"Payload Stripe invalide")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400,"Signature Stripe invalide")
    event_type=event.get("type","")
    obj=event.get("data",{}).get("object",{})
    metadata=obj.get("metadata") or {}
    order_id_raw=metadata.get("order_id") or obj.get("client_reference_id")
    try:
        order_id=int(order_id_raw)
    except (TypeError,ValueError):
        return {"ok":True}
    order=db.get(Order,order_id)
    payment=db.scalar(select(Payment).where(Payment.order_id==order_id))
    if not order or not payment:
        return {"ok":True}
    if event_type in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        if payment.status!="PAYE":
            payment.status="PAYE"
            payment.method="STRIPE"
            payment.reference=obj.get("payment_intent") or obj.get("id") or payment.reference
            order.status=metadata.get("post_payment_status") or ("CONFIRMEE" if order.status=="PAIEMENT_EN_ATTENTE" else order.status)
            delivery=db.scalar(select(Delivery).where(Delivery.order_id==order_id))
            if delivery and delivery.status=="PAIEMENT_EN_ATTENTE":
                delivery.status="A_PREPARER"
            audit(db,"STRIPE_PAYMENT_PAID",f"order_id={order_id};event={event.get('id','-')}")
            db.commit()
    elif event_type in ("checkout.session.expired","checkout.session.async_payment_failed"):
        if payment.status!="PAYE" and order.status!="ANNULEE":
            payment.status="EXPIRE" if event_type.endswith("expired") else "ECHEC"
            _release_unpaid_order(db,order)
            audit(db,"STRIPE_PAYMENT_FAILED",f"order_id={order_id};event={event.get('id','-')};type={event_type}")
            db.commit()
    return {"ok":True}

@app.get("/payments")
def payments(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for p in db.scalars(select(Payment).order_by(Payment.id.desc())).all():
        o=db.get(Order,p.order_id)
        out.append({"id":p.id,"order_id":p.order_id,"client_name":o.client.name if o else "—","status":p.status,"method":p.method,"amount":p.amount,"reference":p.reference})
    return out

@app.post("/payments/{order_id}/mark-paid")
def mark_payment_paid(order_id:int,data:PaymentMarkIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA","VENTE"))):
    order=db.get(Order,order_id)
    if not order: raise HTTPException(404,"Commande introuvable")
    payment=db.scalar(select(Payment).where(Payment.order_id==order_id))
    if not payment:
        invoice=db.scalar(select(Invoice).where(Invoice.order_id==order_id))
        amount=invoice.amount_ht if invoice else 0
        payment=Payment(order_id=order_id,status="A_PAYER",method=data.method,amount=amount,reference=data.reference); db.add(payment)
    payment.status="PAYE"; payment.method=data.method; payment.reference=data.reference
    audit(db,"PAYMENT_MARK_PAID",f"order_id={order_id};method={data.method};reference={data.reference or '-'}")
    db.commit(); return {"ok":True,"status":payment.status}

@app.post("/invoices/{invoice_id}/credit-note")
def create_credit_note(invoice_id:int,data:CreditNoteIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    invoice=db.get(Invoice,invoice_id)
    if not invoice or invoice.status!="VALIDEE": raise HTTPException(409,"La facture doit être validée avant création d'un avoir")
    summary=db.scalar(select(InvoiceFiscalSummary).where(InvoiceFiscalSummary.invoice_id==invoice.id))
    if not summary: raise HTTPException(409,"Résumé fiscal introuvable")
    if data.amount_ht>summary.amount_ht: raise HTTPException(400,"Montant d'avoir supérieur au HT de la facture")
    effective_rate=(summary.amount_tax/summary.amount_ht*100) if summary.amount_ht else 0
    tax=round(data.amount_ht*effective_rate/100,2); ttc=round(data.amount_ht+tax,2)
    now=datetime.now(timezone.utc)
    count=(db.scalar(select(func.count(CreditNote.id))) or 0)+1
    number=f"AV-LPFB-{now.year}-{count:06d}"
    c=CreditNote(invoice_id=invoice.id,credit_number=number,reason=data.reason,amount_ht=round(data.amount_ht,2),amount_tax=tax,amount_ttc=ttc,created_at=now.isoformat(),status="BROUILLON")
    db.add(c); audit(db,"CREDIT_NOTE_CREATE",f"invoice_id={invoice.id};credit={number};ht={data.amount_ht}")
    db.commit(); db.refresh(c); return {"id":c.id,"credit_number":c.credit_number,"amount_ht":c.amount_ht,"amount_tax":c.amount_tax,"amount_ttc":c.amount_ttc}

@app.get("/invoices")
def invoices(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for i in db.scalars(select(Invoice).order_by(Invoice.id.desc())).all():
        o=db.get(Order,i.order_id); s=db.scalar(select(InvoiceFiscalSummary).where(InvoiceFiscalSummary.invoice_id==i.id)); p=db.scalar(select(Payment).where(Payment.order_id==i.order_id)); out.append({"id":i.id,"order_id":i.order_id,"client_name":o.client.name if o else "—","amount_ht":round(s.amount_ht if s else i.amount_ht,2),"amount_tax":round(s.amount_tax,2) if s else None,"amount_ttc":round(s.amount_ttc,2) if s else None,"invoice_number":s.invoice_number if s else None,"issued_at":s.issued_at if s else None,"due_date":s.due_date if s else None,"status":i.status,"payment_status":p.status if p else None,"payment_method":p.method if p else None})
    return out
@app.post("/invoices/{invoice_id}/validate")
def validate_invoice(invoice_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    i=db.get(Invoice,invoice_id)
    if not i: raise HTTPException(404,"Facture introuvable")
    summary=compute_invoice_tax_snapshot(db,i,replace_existing=i.status!="VALIDEE")
    if i.status!="VALIDEE":
        now=datetime.now(timezone.utc)
        summary.invoice_number=f"LPFB-{now.year}-{i.id:06d}"
        summary.issued_at=now.isoformat()
        i.status="VALIDEE"
        audit(db,"INVOICE_VALIDATE",f"invoice_id={invoice_id};number={summary.invoice_number}")
    db.commit()
    return {"status":i.status,"invoice_number":summary.invoice_number,"amount_ht":summary.amount_ht,"amount_tax":summary.amount_tax,"amount_ttc":summary.amount_ttc}

@app.get("/suppliers")
def suppliers(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))): return [{"id":x.id,"name":x.name,"city":x.city,"specialty":x.specialty,"active":x.active} for x in db.scalars(select(Supplier).order_by(Supplier.name)).all()]
@app.post("/suppliers")
def create_supplier(data:SupplierIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if db.scalar(select(Supplier).where(Supplier.name==data.name)): raise HTTPException(409,"Fournisseur déjà existant")
    x=Supplier(**data.model_dump()); db.add(x); audit(db,"SUPPLIER_CREATE",data.name); db.commit(); db.refresh(x); return {"id":x.id}



@app.get("/supplier-coverage")
def supplier_coverage(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    products=db.scalars(select(Product).where(Product.active==1).order_by(Product.family,Product.name)).all()
    linked_ids=set(db.scalars(select(SupplierProduct.product_id).where(SupplierProduct.active==1)).all())
    unlinked=[p for p in products if p.id not in linked_ids]
    family_counts={}
    for p in products:
        f=family_counts.setdefault(p.family,{"total":0,"linked":0,"unlinked":0})
        f["total"]+=1
        if p.id in linked_ids: f["linked"]+=1
        else: f["unlinked"]+=1
    open_requests=db.scalars(select(ProcurementRequest).where(ProcurementRequest.status.notin_(["COUVERT","ANNULE"]))).all()
    needs_without_supplier=[]
    for r in open_requests:
        if r.product_id not in linked_ids:
            needs_without_supplier.append({"request_id":r.id,"product_id":r.product_id,"product_name":r.product.name,"requested_qty":r.requested_qty,"status":r.status})
    return {
        "total_products":len(products),
        "linked_products":len(products)-len(unlinked),
        "unlinked_products":len(unlinked),
        "coverage_pct":round(((len(products)-len(unlinked))/len(products))*100,1) if products else 100,
        "families":family_counts,
        "unlinked":[{"product_id":p.id,"reference":p.reference,"name":p.name,"family":p.family} for p in unlinked],
        "needs_without_supplier":needs_without_supplier
    }

@app.post("/supplier-coverage/bulk-link")
def supplier_coverage_bulk_link(data:SupplierCoverageBulkIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    supplier=db.get(Supplier,data.supplier_id)
    if not supplier or not supplier.active: raise HTTPException(404,"Fournisseur introuvable ou inactif")
    created=0; existing=0
    for product_id in data.product_ids:
        p=db.get(Product,product_id)
        if not p: continue
        row=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier.id,SupplierProduct.product_id==p.id))
        if row:
            row.active=1
            if data.lead_time_days is not None: row.lead_time_days=data.lead_time_days
            existing+=1
        else:
            row=SupplierProduct(supplier_id=supplier.id,product_id=p.id,supplier_reference=data.note_reference,last_price_ht=0,min_order_qty=0,lead_time_days=data.lead_time_days,active=1)
            db.add(row); created+=1
    audit(db,"SUPPLIER_COVERAGE_BULK_LINK",f"supplier={supplier.id};created={created};existing={existing};by={user.email}")
    db.commit()
    return {"created":created,"updated":existing}

@app.get("/supplier-products")
def supplier_products(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for x in db.scalars(select(SupplierProduct).order_by(SupplierProduct.supplier_id,SupplierProduct.product_id)).all():
        out.append({"id":x.id,"supplier_id":x.supplier_id,"supplier_name":x.supplier.name,"product_id":x.product_id,"product_name":x.product.name,"supplier_reference":x.supplier_reference,"last_price_ht":x.last_price_ht,"min_order_qty":x.min_order_qty,"lead_time_days":x.lead_time_days,"active":x.active})
    return out

@app.post("/supplier-products")
def create_supplier_product(data:SupplierProductIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if not db.get(Supplier,data.supplier_id) or not db.get(Product,data.product_id): raise HTTPException(404,"Fournisseur ou produit introuvable")
    existing=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==data.supplier_id,SupplierProduct.product_id==data.product_id))
    if existing:
        for k,v in data.model_dump().items(): setattr(existing,k,v)
        row=existing
    else:
        row=SupplierProduct(**data.model_dump()); db.add(row)
    audit(db,"SUPPLIER_PRODUCT_UPSERT",f"supplier={data.supplier_id};product={data.product_id};price={data.last_price_ht}")
    db.commit(); db.refresh(row); return {"id":row.id}

@app.get("/purchase-orders")
def purchase_orders(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for po in db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id.desc())).all():
        lines=[]
        total=0.0
        for l in db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id==po.id)).all():
            amount=l.quantity*l.unit_price_ht; total+=amount
            lines.append({"id":l.id,"product_id":l.product_id,"product_name":l.product.name,"quantity":l.quantity,"unit_price_ht":l.unit_price_ht,"received_qty":l.received_qty,"amount_ht":round(amount,2)})
        out.append({"id":po.id,"supplier_id":po.supplier_id,"supplier_name":po.supplier.name,"status":po.status,"expected_date":po.expected_date,"note":po.note,"created_at":po.created_at,"amount_ht":round(total,2),"lines":lines})
    return out

@app.post("/purchase-orders")
def create_purchase_order(data:PurchaseOrderIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if not db.get(Supplier,data.supplier_id): raise HTTPException(404,"Fournisseur introuvable")
    if not data.lines: raise HTTPException(400,"Aucune ligne d'achat")
    po=PurchaseOrder(supplier_id=data.supplier_id,status="BROUILLON",expected_date=data.expected_date,note=data.note,created_at=datetime.now(timezone.utc).isoformat())
    db.add(po); db.flush()
    for line in data.lines:
        if not db.get(Product,line.product_id): raise HTTPException(404,"Produit introuvable")
        db.add(PurchaseOrderLine(purchase_order_id=po.id,product_id=line.product_id,quantity=line.quantity,unit_price_ht=line.unit_price_ht,received_qty=0))
    audit(db,"PURCHASE_ORDER_CREATE",f"po_id={po.id};supplier={po.supplier_id};lines={len(data.lines)}")
    db.commit(); db.refresh(po); return {"id":po.id,"status":po.status}

@app.post("/purchase-orders/{po_id}/send")
def send_purchase_order(po_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    po=db.get(PurchaseOrder,po_id)
    if not po: raise HTTPException(404,"Commande fournisseur introuvable")
    if po.status not in ("BROUILLON","A_VALIDER"): raise HTTPException(409,"Cette commande ne peut plus être envoyée")
    po.status="ENVOYEE"
    audit(db,"PURCHASE_ORDER_SEND",f"po_id={po.id};supplier={po.supplier_id}")
    db.commit(); return {"ok":True,"status":po.status}

@app.post("/purchase-orders/{po_id}/receive")
def receive_purchase_order(po_id:int,data:PurchaseReceiptIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","PRODUCTION"))):
    po=db.get(PurchaseOrder,po_id)
    if not po: raise HTTPException(404,"Commande fournisseur introuvable")
    if po.status=="ANNULEE": raise HTTPException(409,"Commande annulée")
    if not data.lines: raise HTTPException(400,"Réception vide")
    receipt=PurchaseReceipt(purchase_order_id=po.id,received_at=datetime.now(timezone.utc).isoformat(),note=data.note)
    db.add(receipt); db.flush()
    for item in data.lines:
        line=db.get(PurchaseOrderLine,item.purchase_order_line_id)
        if not line or line.purchase_order_id!=po.id: raise HTTPException(400,"Ligne de commande invalide")
        if db.scalar(select(Lot).where(Lot.internal_lot==item.internal_lot)): raise HTTPException(409,f"Lot interne {item.internal_lot} déjà utilisé")
        status=item.lot_status.upper()
        if status not in ("BLOQUE","LIBERE"): raise HTTPException(400,"Statut lot attendu : BLOQUE ou LIBERE")
        line.received_qty += item.received_qty
        lot=Lot(product_id=line.product_id,internal_lot=item.internal_lot,supplier_lot=item.supplier_lot,qty_received=item.received_qty,qty_reserved=0,qty_consumed=0,expiry_date=item.expiry_date,status=status)
        db.add(lot); db.flush(); set_lot_stage(db,lot.id,"RAW","SUPPLIER_RECEIPT")
        db.add(PurchaseReceiptLine(receipt_id=receipt.id,purchase_order_line_id=line.id,received_qty=item.received_qty,internal_lot=item.internal_lot,supplier_lot=item.supplier_lot,expiry_date=item.expiry_date,lot_status=status))
        reconcile_procurement_receipt(db,line.id,item.received_qty)
    all_lines=db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id==po.id)).all()
    po.status="RECUE" if all(l.received_qty>=l.quantity for l in all_lines) else "PARTIELLEMENT_RECUE"
    audit(db,"PURCHASE_RECEIPT",f"po_id={po.id};receipt_id={receipt.id};status={po.status}")
    db.commit(); return {"ok":True,"receipt_id":receipt.id,"status":po.status}

@app.post("/purchase-orders/{po_id}/cancel")
def cancel_purchase_order(po_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    po=db.get(PurchaseOrder,po_id)
    if not po: raise HTTPException(404,"Commande fournisseur introuvable")
    if po.status in ("RECUE","PARTIELLEMENT_RECUE"): raise HTTPException(409,"Une commande déjà reçue ne peut pas être annulée")
    po.status="ANNULEE"; audit(db,"PURCHASE_ORDER_CANCEL",f"po_id={po.id}"); db.commit(); return {"ok":True}

@app.get("/equipment")
def equipment(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))): return [{"id":x.id,"name":x.name,"budget_low":x.budget_low,"budget_high":x.budget_high,"priority":x.priority,"status":x.status} for x in db.scalars(select(Equipment).order_by(Equipment.id)).all()]
@app.post("/equipment")
def create_equipment(data:EquipmentIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    x=Equipment(**data.model_dump()); db.add(x); audit(db,"EQUIPMENT_CREATE",data.name); db.commit(); db.refresh(x); return {"id":x.id}

@app.get("/settings")
def settings(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))): return {x.key:x.value for x in db.scalars(select(AppSetting)).all()}
@app.put("/settings/{key}")
def update_setting(key:str,data:SettingIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    x=db.scalar(select(AppSetting).where(AppSetting.key==key))
    if not x: x=AppSetting(key=key,value=data.value); db.add(x)
    else: x.value=data.value
    audit(db,"SETTING_UPDATE",f"{key}={data.value}"); db.commit(); return {"key":key,"value":data.value}

@app.get("/preparations")
def preparations(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for x in db.scalars(select(PreparationProfile).order_by(PreparationProfile.product_id,PreparationProfile.cut_name)).all():
        out.append({"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"cut_name":x.cut_name,"portion_g":x.portion_g,"yield_rate":x.yield_rate,"b2c_formats":x.b2c_formats,"pro_formats":x.pro_formats,"uses":x.uses})
    return out

@app.get("/packaging-formats")
def packaging_formats(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    return [{"id":x.id,"segment":x.segment,"label":x.label,"quantity_g":x.quantity_g,"recommended_use":x.recommended_use} for x in db.scalars(select(PackagingFormat).order_by(PackagingFormat.segment,PackagingFormat.quantity_g)).all()]

@app.get("/recipes")
def recipes(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    out=[]
    for r in db.scalars(select(Recipe).where(Recipe.active==1).order_by(Recipe.name)).all():
        ings=[]
        for i in db.scalars(select(RecipeIngredient).where(RecipeIngredient.recipe_id==r.id)).all():
            ings.append({"product_id":i.product_id,"product_name":i.product.name,"grams_per_serving":i.grams_per_serving,"cut_name":i.cut_name})
        out.append({"id":r.id,"name":r.name,"category":r.category,"default_servings":r.default_servings,"description":r.description,"ingredients":ings})
    return out

@app.post("/calculators/portion")
def calc_portion(data:PortionCalcIn,db:Session=Depends(get_db)):
    product=db.get(Product,data.product_id)
    if not product: raise HTTPException(404,"Produit introuvable")
    prof=None
    if data.cut_name:
        prof=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==data.product_id,PreparationProfile.cut_name==data.cut_name))
    if not prof:
        prof=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==data.product_id))
    portion=data.grams_per_serving or (prof.portion_g if prof else 100)
    yield_rate=(prof.yield_rate if prof else 1.0)
    net_g=portion*data.servings
    gross_g=net_g/max(yield_rate,.01)
    formats=[x for x in db.scalars(select(PackagingFormat).where(PackagingFormat.segment=="B2C").order_by(PackagingFormat.quantity_g)).all()]
    recommended=next((x.quantity_g for x in formats if x.quantity_g>=net_g),formats[-1].quantity_g if formats else net_g)
    return {"product":product.name,"servings":data.servings,"portion_g":round(portion,1),"net_g":round(net_g,1),"gross_g":round(gross_g,1),"yield_rate":yield_rate,"recommended_pack_g":recommended,"cut_name":data.cut_name}

@app.post("/calculators/pro")
def calc_pro(data:ProCalcIn,db:Session=Depends(get_db)):
    product=db.get(Product,data.product_id)
    if not product: raise HTTPException(404,"Produit introuvable")
    prof=None
    if data.cut_name:
        prof=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==data.product_id,PreparationProfile.cut_name==data.cut_name))
    yield_rate=prof.yield_rate if prof else 1.0
    net_kg=(data.covers*data.grams_per_cover)/1000
    gross_kg=net_kg/max(yield_rate,.01)
    formats=[x.quantity_g/1000 for x in db.scalars(select(PackagingFormat).where(PackagingFormat.segment=="PRO").order_by(PackagingFormat.quantity_g.desc())).all()]
    packs=[]; remaining=net_kg
    for f in formats:
        n=int(remaining//f)
        if n>0: packs.append({"kg":f,"count":n}); remaining-=n*f
    if remaining>0 and formats:
        small=min(formats); packs.append({"kg":small,"count":1})
    return {"product":product.name,"covers":data.covers,"grams_per_cover":data.grams_per_cover,"net_kg":round(net_kg,2),"gross_kg":round(gross_kg,2),"yield_rate":yield_rate,"suggested_packs":packs,"cut_name":data.cut_name}

@app.get("/public/recipes")
def public_recipes(db:Session=Depends(get_db)):
    out=[]
    for r in db.scalars(select(Recipe).where(Recipe.active==1).order_by(Recipe.name)).all():
        ings=[]
        for i in db.scalars(select(RecipeIngredient).where(RecipeIngredient.recipe_id==r.id)).all():
            ings.append({"product_id":i.product_id,"product_name":i.product.name,"grams_per_serving":i.grams_per_serving,"cut_name":i.cut_name})
        out.append({"id":r.id,"name":r.name,"category":r.category,"default_servings":r.default_servings,"description":r.description,"ingredients":ings})
    return out

@app.post("/calculators/recipe")
def calc_recipe(data:RecipeCalcIn,db:Session=Depends(get_db)):
    r=db.get(Recipe,data.recipe_id)
    if not r or not r.active: raise HTTPException(404,"Recette introuvable")
    result=[]; total_net=0.0; total_gross=0.0
    for i in db.scalars(select(RecipeIngredient).where(RecipeIngredient.recipe_id==r.id)).all():
        prof=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==i.product_id,PreparationProfile.cut_name==i.cut_name)) if i.cut_name else None
        y=prof.yield_rate if prof else 1.0
        net=i.grams_per_serving*data.servings; gross=net/max(y,.01)
        total_net+=net; total_gross+=gross
        result.append({"product_id":i.product_id,"product_name":i.product.name,"cut_name":i.cut_name,"net_g":round(net,1),"gross_g":round(gross,1),"yield_rate":y})
    return {"recipe_id":r.id,"recipe_name":r.name,"servings":data.servings,"ingredients":result,"total_net_g":round(total_net,1),"total_gross_g":round(total_gross,1)}


def readiness_checks(db:Session):
    active_products=db.scalars(select(Product).where(Product.active==1)).all()
    tax_configured={x.product_id for x in db.scalars(select(ProductTaxProfile)).all()}
    cost_configured={x.product_id for x in db.scalars(select(ProductCostProfile)).all()}
    missing_tax=[p.name for p in active_products if p.id not in tax_configured]
    missing_cost=[p.name for p in active_products if p.id not in cost_configured]
    admin_count=db.scalar(select(func.count(User.id)).where(User.role=="ADMIN",User.active==1)) or 0
    demo_emails=[DEMO_ADMIN_EMAIL,DEMO_PRO_EMAIL,DEMO_B2C_EMAIL]
    demo_users=db.scalars(select(User).where(User.email.in_(demo_emails),User.active==1)).all()
    blocked_lots=db.scalar(select(func.count(Lot.id)).where(Lot.status=="BLOQUE")) or 0
    open_production=db.scalar(select(func.count(ProductionJob.id)).where(ProductionJob.status.notin_(["TERMINE","ANNULE"]))) or 0
    draft_invoices=db.scalar(select(func.count(Invoice.id)).where(Invoice.status!="VALIDEE")) or 0
    checklist=[
        {"code":"DATABASE","label":"Base PostgreSQL persistante","status":"PASS" if DATABASE_URL.startswith("postgresql") else "BLOCK","detail":"PostgreSQL détecté." if DATABASE_URL.startswith("postgresql") else "SQLite détecté : ne pas ouvrir la production avec cette base."},
        {"code":"STRICT","label":"Garde-fous production","status":"PASS" if not production_config_errors() else "BLOCK","detail":"Configuration technique de production valide." if not production_config_errors() else " | ".join(production_config_errors())},
        {"code":"SECRET","label":"Clé secrète de production","status":"PASS" if SECRET_KEY!="CHANGE-ME-IN-RENDER" and len(SECRET_KEY)>=32 else "BLOCK","detail":"SECRET_KEY personnalisée." if SECRET_KEY!="CHANGE-ME-IN-RENDER" and len(SECRET_KEY)>=32 else "Définir une SECRET_KEY forte (32+ caractères)."},
        {"code":"CORS","label":"Origines web restreintes","status":"PASS" if "*" not in ALLOWED_ORIGINS else "WARN","detail":", ".join(ALLOWED_ORIGINS) if "*" not in ALLOWED_ORIGINS else "ALLOWED_ORIGINS autorise encore toutes les origines."},
        {"code":"DEMO","label":"Comptes de démonstration","status":"PASS" if not demo_users else "BLOCK","detail":"Aucun compte démo actif." if not demo_users else f"{len(demo_users)} compte(s) de démonstration actif(s)."},
        {"code":"DEMO_SEED","label":"Réinjection des données de démonstration","status":"PASS" if not (ENVIRONMENT=="production" and SEED_DEMO_DATA) else "BLOCK","detail":"SEED_DEMO_DATA désactivé pour la production." if not (ENVIRONMENT=="production" and SEED_DEMO_DATA) else "SEED_DEMO_DATA est actif : les comptes démo seraient recréés au redémarrage."},
        {"code":"ADMIN","label":"Administrateur actif","status":"PASS" if admin_count>=1 else "BLOCK","detail":f"{admin_count} administrateur(s) actif(s)."},
        {"code":"TAX","label":"Fiscalité configurée sur le catalogue actif","status":"PASS" if not missing_tax else "WARN","detail":"Tous les produits actifs ont un profil fiscal." if not missing_tax else f"{len(missing_tax)} produit(s) actif(s) sans profil fiscal.","items":missing_tax[:15]},
        {"code":"COST","label":"Coûts renseignés sur le catalogue actif","status":"PASS" if not missing_cost else "WARN","detail":"Tous les produits actifs ont un profil de coût." if not missing_cost else f"{len(missing_cost)} produit(s) actif(s) sans profil de coût.","items":missing_cost[:15]},
        {"code":"BLOCKED_LOTS","label":"Lots bloqués","status":"PASS" if blocked_lots==0 else "WARN","detail":f"{blocked_lots} lot(s) bloqué(s) à traiter." if blocked_lots else "Aucun lot bloqué."},
        {"code":"OPEN_PRODUCTION","label":"Productions en cours","status":"PASS" if open_production==0 else "WARN","detail":f"{open_production} production(s) non terminée(s)."},
        {"code":"DRAFT_INVOICES","label":"Factures non validées","status":"PASS" if draft_invoices==0 else "WARN","detail":f"{draft_invoices} facture(s) non validée(s)."},
    ]
    blocks=sum(1 for x in checklist if x["status"]=="BLOCK")
    warns=sum(1 for x in checklist if x["status"]=="WARN")
    ready=blocks==0
    return {"ready_for_production":ready,"blocking_count":blocks,"warning_count":warns,"checks":checklist}

@app.get("/preproduction/readiness")
def preproduction_readiness(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    return readiness_checks(db)

@app.get("/preproduction/report")
def preproduction_report(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    report=readiness_checks(db)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    report["application"]="Le Panier Frais Bio"
    report["version"]="1.0.0"
    report["database"]="postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite"
    audit(db,"PREPRODUCTION_REPORT","readiness export"); db.commit()
    return JSONResponse(report,headers={"Content-Disposition":"attachment; filename=LPFB-preproduction-readiness.json"})


@app.post("/preproduction/smoke-test")
def preproduction_smoke_test(data:PreproductionSmokeTestIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    results=[]
    def record(name,ok,detail):
        results.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})
    try:
        # 1. Core catalogue/read checks
        product=db.scalar(select(Product).where(Product.active==1).order_by(Product.id.asc()))
        record("Catalogue actif",bool(product),product.name if product else "Aucun produit actif")
        supplier=db.scalar(select(Supplier).where(Supplier.active==1).order_by(Supplier.id.asc()))
        record("Fournisseur disponible",bool(supplier),supplier.name if supplier else "Aucun fournisseur actif")
        staff_count=db.scalar(select(func.count(User.id)).where(User.role.in_(STAFF_ROLES),User.active==1)) or 0
        record("Comptes équipe actifs",staff_count>0,f"{staff_count} compte(s)")

        if data.include_write_cycle and product:
            # All objects below are rolled back at the end: this is a transaction-only dry run.
            stamp=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            client=Client(client_type="B2C",name=f"QA Client {stamp}",email=f"qa-{stamp}@example.invalid",active=1)
            db.add(client); db.flush()
            record("Création client transactionnelle",client.id is not None,f"id temporaire {client.id}")

            order=Order(client_id=client.id,status="CONFIRMEE",delivery_mode="CLICK_COLLECT",created_at=datetime.now(timezone.utc).isoformat())
            db.add(order); db.flush()
            line=OrderLine(order_id=order.id,product_id=product.id,quantity=1,unit_price_ht=product.price_ht)
            db.add(line)
            db.add(OrderOption(order_id=order.id,cut_name=None,note="QA dry-run"))
            db.add(Delivery(order_id=order.id,status="A_PREPARER",slot="QA"))
            invoice=Invoice(order_id=order.id,status="BROUILLON",amount_ht=product.price_ht)
            db.add(invoice)
            payment=Payment(order_id=order.id,status="A_PAYER",method="QA",amount=product.price_ht,reference="QA-ROLLBACK")
            db.add(payment); db.flush()
            record("Commande / livraison / facture / paiement",all([order.id,invoice.id,payment.id]),f"commande temporaire #{order.id}")

            # Tax snapshot on the same uncommitted invoice.
            summary=compute_invoice_tax_snapshot(db,invoice,replace_existing=True)
            db.flush()
            tax_line_count=db.scalar(select(func.count(InvoiceTaxLine.id)).where(InvoiceTaxLine.invoice_id==invoice.id)) or 0
            record("Calcul fiscal facture",summary is not None and tax_line_count>=1,f"{tax_line_count} ligne(s), TTC {summary.amount_ttc}")

            # Stock + production lineage dry run.
            source_lot=Lot(product_id=product.id,internal_lot=f"QA-SRC-{stamp}",supplier_lot="QA-SUP",qty_received=10,qty_reserved=0,qty_consumed=0,expiry_date=None,status="LIBERE")
            db.add(source_lot); db.flush()
            job=ProductionJob(product_id=product.id,quantity_needed=1,status="EN_PREPARATION",source_order_id=order.id,created_at=datetime.now(timezone.utc).isoformat())
            db.add(job); db.flush()
            output_lot=Lot(product_id=product.id,internal_lot=f"QA-OUT-{stamp}",supplier_lot=None,qty_received=.9,qty_reserved=0,qty_consumed=0,expiry_date=None,status="LIBERE")
            db.add(output_lot); db.flush()
            batch=ProductionBatch(job_id=job.id,output_lot_id=output_lot.id,cut_name=None,packaging="QA",actual_input_qty=1,actual_output_qty=.9,temperature_c=None,quality_status="VALIDEE",operator_notes="QA dry-run",completed_at=datetime.now(timezone.utc).isoformat())
            db.add(batch); db.flush()
            db.add(ProductionConsumption(batch_id=batch.id,source_lot_id=source_lot.id,quantity=1))
            source_lot.qty_consumed += 1
            job.status="TERMINE"
            db.flush()
            lineage_count=db.scalar(select(func.count(ProductionConsumption.id)).where(ProductionConsumption.batch_id==batch.id)) or 0
            record("Production & traçabilité",lineage_count==1,f"batch temporaire #{batch.id}")

            # Supplier purchase dry run when a supplier exists.
            if supplier:
                po=PurchaseOrder(supplier_id=supplier.id,status="BROUILLON",expected_date=None,note="QA dry-run",created_at=datetime.now(timezone.utc).isoformat())
                db.add(po); db.flush()
                pol=PurchaseOrderLine(purchase_order_id=po.id,product_id=product.id,quantity=2,unit_price_ht=1,received_qty=0)
                db.add(pol); db.flush()
                receipt=PurchaseReceipt(purchase_order_id=po.id,received_at=datetime.now(timezone.utc).isoformat(),note="QA dry-run")
                db.add(receipt); db.flush()
                rec_line=PurchaseReceiptLine(receipt_id=receipt.id,purchase_order_line_id=pol.id,received_qty=2,internal_lot=f"QA-REC-{stamp}",supplier_lot="QA-SUP",expiry_date=None,lot_status="BLOQUE")
                db.add(rec_line); db.flush()
                record("Achat fournisseur & réception",receipt.id is not None,f"bon temporaire #{po.id}")
            else:
                record("Achat fournisseur & réception",False,"Aucun fournisseur actif pour exécuter ce test")

        passed=sum(1 for r in results if r["status"]=="PASS")
        failed=sum(1 for r in results if r["status"]=="FAIL")
        audit(db,"PREPRODUCTION_SMOKE_TEST",f"pass={passed};fail={failed};write_cycle={data.include_write_cycle}")
        # Important: rollback intentionally removes the whole dry-run, including audit event.
        db.rollback()
        return {"status":"PASS" if failed==0 else "FAIL","passed":passed,"failed":failed,"rolled_back":True,"results":results,"notice":"Toutes les écritures de ce test ont été annulées par rollback."}
    except Exception as exc:
        db.rollback()
        return {"status":"FAIL","passed":sum(1 for r in results if r["status"]=="PASS"),"failed":1,"rolled_back":True,"results":results+[{"name":"Exception test fonctionnel","status":"FAIL","detail":str(exc)}],"notice":"Rollback effectué après erreur."}

@app.get("/alerts")
def alerts(db:Session=Depends(get_db),user=Depends(roles(*STAFF_ROLES))):
    today=date.today(); out=[]
    for l in db.scalars(select(Lot)).all():
        if l.status=="BLOQUE": out.append({"level":"CRITIQUE","type":"LOT_BLOQUE","message":f"Lot {l.internal_lot} bloqué - {l.product.name}"})
        if l.expiry_date:
            try:
                days=(date.fromisoformat(l.expiry_date)-today).days
                if days<=3: out.append({"level":"ALERTE" if days>=0 else "CRITIQUE","type":"DLC","message":f"{l.product.name} / {l.internal_lot} : DLC dans {days} j"})
            except ValueError: pass
    for o in db.scalars(select(Order).where(Order.status=="CONFIRMEE")).all():
        out.append({"level":"INFO","type":"COMMANDE","message":f"Commande #{o.id} à préparer - {o.client.name}"})
    return out[:50]



@app.get("/availability/products")
def availability_products(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    out=[]
    for p in db.scalars(select(Product).where(Product.active==1).order_by(Product.family,Product.name)).all():
        a=db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==p.id))
        stock=available_stock_for_product(db,p.id)
        out.append({"product_id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"price_ht":p.price_ht,"stock_available":stock,"order_mode":a.order_mode if a else "SUR_COMMANDE","supplier_lead_days":a.supplier_lead_days if a else 2,"allow_order":bool(a.allow_order) if a else True,"notes":a.notes if a else ""})
    return out

@app.put("/availability/products/{product_id}")
def update_availability(product_id:int,data:ProductAvailabilityIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Produit introuvable")
    if data.order_mode not in ("EN_STOCK","SUR_COMMANDE","SAISONNIER","INDISPONIBLE"):
        raise HTTPException(400,"Mode attendu : EN_STOCK, SUR_COMMANDE, SAISONNIER ou INDISPONIBLE")
    row=db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==product_id))
    if not row:
        row=ProductAvailability(product_id=product_id); db.add(row)
    row.order_mode=data.order_mode; row.supplier_lead_days=data.supplier_lead_days; row.allow_order=1 if data.allow_order else 0; row.notes=data.notes
    audit(db,"PRODUCT_AVAILABILITY_UPDATE",f"product_id={product_id};mode={data.order_mode};allow={data.allow_order};by={user.email}")
    db.commit(); return {"ok":True}

@app.get("/procurement/requests")
def procurement_requests(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    rows=db.scalars(select(ProcurementRequest).order_by(ProcurementRequest.id.desc())).all()
    return [{"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"requested_qty":x.requested_qty,"source_type":x.source_type,"source_order_id":x.source_order_id,"client_id":x.client_id,"status":x.status,"note":x.note,"created_at":x.created_at} for x in rows]

@app.post("/public/sourcing-request")
def public_sourcing_request(data:ProductSourcingRequestIn,db:Session=Depends(get_db)):
    p=db.get(Product,data.product_id)
    if not p or not p.active: raise HTTPException(404,"Produit introuvable")
    a=db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==p.id))
    if a and not a.allow_order: raise HTTPException(409,"Produit actuellement indisponible à la commande")
    row=ProductSourcingRequest(product_id=p.id,customer_email=data.customer_email,quantity=data.quantity,note=data.note,status="A_TRAITER",created_at=datetime.now(timezone.utc).isoformat())
    db.add(row)
    create_procurement_need(db,p,data.quantity,"DEMANDE_CLIENT",None,None,f"Demande catalogue: {data.customer_email or 'sans compte'}")
    db.commit(); db.refresh(row)
    return {"request_id":row.id,"status":row.status,"message":"Demande enregistrée. Approvisionnement fournisseur à confirmer."}


@app.get("/procurement/requests/{request_id}/supplier-options")
def procurement_supplier_options(request_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    req=db.get(ProcurementRequest,request_id)
    if not req: raise HTTPException(404,"Besoin d'approvisionnement introuvable")
    linked=db.scalars(select(SupplierProduct).where(SupplierProduct.product_id==req.product_id,SupplierProduct.active==1).order_by(SupplierProduct.last_price_ht.asc())).all()
    linked_ids={x.supplier_id for x in linked}
    options=[]
    for x in linked:
        options.append({"supplier_id":x.supplier_id,"supplier_name":x.supplier.name,"last_price_ht":x.last_price_ht,"min_order_qty":x.min_order_qty,"lead_time_days":x.lead_time_days,"supplier_reference":x.supplier_reference,"linked":True})
    # Fallback: every active supplier can still be proposed manually. This does not assert that the supplier stocks the product.
    for s in db.scalars(select(Supplier).where(Supplier.active==1).order_by(Supplier.name)).all():
        if s.id not in linked_ids:
            options.append({"supplier_id":s.id,"supplier_name":s.name,"last_price_ht":0,"min_order_qty":0,"lead_time_days":None,"supplier_reference":None,"linked":False})
    return {"request_id":req.id,"product_id":req.product_id,"product_name":req.product.name,"requested_qty":req.requested_qty,"options":options}

@app.put("/procurement/requests/{request_id}/status")
def procurement_request_status(request_id:int,data:ProcurementStatusIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    req=db.get(ProcurementRequest,request_id)
    if not req: raise HTTPException(404,"Besoin d'approvisionnement introuvable")
    allowed=("A_APPROVISIONNER","EN_COURS","COMMANDE_FOURNISSEUR","COUVERT","ANNULE")
    status=data.status.upper()
    if status not in allowed: raise HTTPException(400,"Statut d'approvisionnement invalide")
    req.status=status
    audit(db,"PROCUREMENT_STATUS",f"request_id={request_id};status={status};by={user.email}")
    db.commit(); return {"ok":True,"status":status}

@app.post("/procurement/convert-to-purchase-orders")
def procurement_convert(data:ProcurementConvertIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    if not data.lines: raise HTTPException(400,"Aucun besoin sélectionné")
    grouped={}
    for item in data.lines:
        req=db.get(ProcurementRequest,item.request_id)
        if not req: raise HTTPException(404,f"Besoin {item.request_id} introuvable")
        if req.status in ("COUVERT","ANNULE"): raise HTTPException(409,f"Besoin {req.id} déjà traité")
        supplier=db.get(Supplier,item.supplier_id)
        if not supplier or not supplier.active: raise HTTPException(404,"Fournisseur introuvable ou inactif")
        link=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier.id,SupplierProduct.product_id==req.product_id))
        if not link:
            link=SupplierProduct(supplier_id=supplier.id,product_id=req.product_id,supplier_reference=None,last_price_ht=item.unit_price_ht,min_order_qty=0,lead_time_days=0,active=1)
            db.add(link)
        elif item.unit_price_ht>0:
            link.last_price_ht=item.unit_price_ht
        grouped.setdefault(item.supplier_id,[]).append((req,item.unit_price_ht))
    created=[]
    for supplier_id,items in grouped.items():
        po=PurchaseOrder(supplier_id=supplier_id,status="BROUILLON",expected_date=data.expected_date,note=data.note,created_at=datetime.now(timezone.utc).isoformat())
        db.add(po); db.flush()
        for req,price in items:
            pol=PurchaseOrderLine(purchase_order_id=po.id,product_id=req.product_id,quantity=req.requested_qty,unit_price_ht=price,received_qty=0)
            db.add(pol); db.flush()
            db.add(ProcurementPurchaseLink(procurement_request_id=req.id,purchase_order_line_id=pol.id,allocated_qty=req.requested_qty,fulfilled_qty=0))
            req.status="COMMANDE_FOURNISSEUR"
            req.note=(req.note+" | " if req.note else "")+f"Bon fournisseur #{po.id}"
        created.append({"purchase_order_id":po.id,"supplier_id":supplier_id,"lines":len(items)})
    audit(db,"PROCUREMENT_CONVERT_TO_PO",f"purchase_orders={len(created)};requests={len(data.lines)};by={user.email}")
    db.commit()
    return {"created":created}


@app.get("/procurement/requests/{request_id}/trace")
def procurement_request_trace(request_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE","PRODUCTION"))):
    req=db.get(ProcurementRequest,request_id)
    if not req: raise HTTPException(404,"Besoin d'approvisionnement introuvable")
    links=db.scalars(select(ProcurementPurchaseLink).where(ProcurementPurchaseLink.procurement_request_id==req.id).order_by(ProcurementPurchaseLink.id)).all()
    purchase=[]
    for link in links:
        pol=db.get(PurchaseOrderLine,link.purchase_order_line_id)
        po=db.get(PurchaseOrder,pol.purchase_order_id) if pol else None
        purchase.append({
            "purchase_order_id":po.id if po else None,
            "purchase_order_status":po.status if po else None,
            "supplier_name":po.supplier.name if po else None,
            "allocated_qty":link.allocated_qty,
            "fulfilled_qty":link.fulfilled_qty,
            "product_name":req.product.name
        })
    return {"request_id":req.id,"product_name":req.product.name,"requested_qty":req.requested_qty,"status":req.status,"source_order_id":req.source_order_id,"purchase":purchase}

@app.get("/procurement/dashboard")
def procurement_dashboard(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    rows=db.scalars(select(ProcurementRequest).order_by(ProcurementRequest.id.desc())).all()
    status_counts={}
    qty_total=0.0
    products={}
    for r in rows:
        status_counts[r.status]=status_counts.get(r.status,0)+1
        if r.status not in ("COUVERT","ANNULE"):
            qty_total+=r.requested_qty
            products.setdefault(r.product_id,{"product_name":r.product.name,"qty":0.0,"requests":0})
            products[r.product_id]["qty"]+=r.requested_qty
            products[r.product_id]["requests"]+=1
    top=sorted(products.values(),key=lambda x:x["qty"],reverse=True)[:10]
    in_transit_qty=0.0; fulfilled_qty=0.0
    for link in db.scalars(select(ProcurementPurchaseLink)).all():
        in_transit_qty += max(0,link.allocated_qty-link.fulfilled_qty)
        fulfilled_qty += link.fulfilled_qty
    return {"status_counts":status_counts,"open_quantity":round(qty_total,3),"top_needs":top,"open_requests":sum(v for k,v in status_counts.items() if k not in ("COUVERT","ANNULE")),"in_transit_qty":round(in_transit_qty,3),"fulfilled_qty":round(fulfilled_qty,3)}

@app.get("/public/product-media")
def public_product_media(db:Session=Depends(get_db)):
    rows=db.scalars(select(ProductMedia).where(ProductMedia.active==1)).all()
    return [{"product_id":x.product_id,"image_url":x.image_url,"alt_text":x.alt_text,"badge":x.badge} for x in rows]

@app.get("/public/marketing-visuals")
def public_marketing_visuals(db:Session=Depends(get_db)):
    rows=db.scalars(select(MarketingVisual).where(MarketingVisual.active==1).order_by(MarketingVisual.sort_order,MarketingVisual.id)).all()
    return [{"id":x.id,"placement":x.placement,"title":x.title,"subtitle":x.subtitle,"image_url":x.image_url,"target_filter":x.target_filter,"sort_order":x.sort_order} for x in rows]

@app.get("/media/products")
def media_products(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    rows=db.scalars(select(ProductMedia).order_by(ProductMedia.product_id)).all()
    return [{"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"image_url":x.image_url,"alt_text":x.alt_text,"badge":x.badge,"active":bool(x.active)} for x in rows]

@app.post("/media/products")
def upsert_product_media(data:ProductMediaIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if not db.get(Product,data.product_id): raise HTTPException(404,"Produit introuvable")
    row=db.scalar(select(ProductMedia).where(ProductMedia.product_id==data.product_id))
    if not row:
        row=ProductMedia(product_id=data.product_id,image_url=data.image_url); db.add(row)
    row.image_url=data.image_url; row.alt_text=data.alt_text; row.badge=data.badge; row.active=1 if data.active else 0
    audit(db,"PRODUCT_MEDIA_UPSERT",f"product_id={data.product_id};url={data.image_url};by={user.email}")
    db.commit(); db.refresh(row); return {"id":row.id}

@app.get("/marketing-visuals")
def marketing_visuals(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    rows=db.scalars(select(MarketingVisual).order_by(MarketingVisual.sort_order,MarketingVisual.id)).all()
    return [{"id":x.id,"placement":x.placement,"title":x.title,"subtitle":x.subtitle,"image_url":x.image_url,"target_filter":x.target_filter,"active":bool(x.active),"sort_order":x.sort_order} for x in rows]

@app.post("/marketing-visuals")
def create_marketing_visual(data:MarketingVisualIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    row=MarketingVisual(placement=data.placement,title=data.title,subtitle=data.subtitle,image_url=data.image_url,target_filter=data.target_filter,active=1 if data.active else 0,sort_order=data.sort_order)
    db.add(row); audit(db,"MARKETING_VISUAL_CREATE",f"{data.placement};{data.title};by={user.email}"); db.commit(); db.refresh(row); return {"id":row.id}

@app.put("/marketing-visuals/{visual_id}")
def update_marketing_visual(visual_id:int,data:MarketingVisualIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    row=db.get(MarketingVisual,visual_id)
    if not row: raise HTTPException(404,"Visuel introuvable")
    for k,v in data.model_dump().items():
        setattr(row,k,1 if k=="active" and v else 0 if k=="active" else v)
    audit(db,"MARKETING_VISUAL_UPDATE",f"id={visual_id};by={user.email}"); db.commit(); return {"ok":True}

@app.get("/public/catalog")
def public_catalog(db:Session=Depends(get_db)):
    out=[]
    for p in db.scalars(select(Product).where(Product.active==1).order_by(Product.family,Product.name)).all():
        cut_rows=db.scalars(select(ProductCut).where(ProductCut.product_id==p.id)).all()
        cuts=[{"name":c.cut_name,"yield_rate":c.yield_rate,"extra_price_ht":c.extra_price_ht} for c in cut_rows]
        prof=db.scalar(select(PreparationProfile).where(PreparationProfile.product_id==p.id))
        avail=db.scalar(select(ProductAvailability).where(ProductAvailability.product_id==p.id))
        stock=available_stock_for_product(db,p.id)
        out.append({"id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"unit":p.unit,"price_ht":p.price_ht,"price_configured":p.price_ht>0,"stock_available":stock,"order_mode":avail.order_mode if avail else ("EN_STOCK" if stock>0 else "SUR_COMMANDE"),"supplier_lead_days":avail.supplier_lead_days if avail else 2,"allow_order":bool(avail.allow_order) if avail else True,"availability_notes":avail.notes if avail else "","cuts":cuts,"portion_g":prof.portion_g if prof else None,"uses":prof.uses if prof else "","b2c_formats":prof.b2c_formats if prof else "250 g, 500 g, 750 g, 1 kg","pro_formats":prof.pro_formats if prof else "1 kg, 2.5 kg, 5 kg, 10 kg"})
    return out

@app.get("/audit")
def audit_log(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))): return [{"created_at":x.created_at,"event_type":x.event_type,"details":x.details} for x in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()]

@app.get("/backup")
def backup(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    payload={
        "schema":"LPFB_BACKUP_1_0_0",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "products":[{"id":x.id,"reference":x.reference,"name":x.name,"family":x.family,"unit":x.unit,"price_ht":x.price_ht,"active":x.active} for x in db.scalars(select(Product)).all()],
        "product_cuts":[{"product_id":x.product_id,"cut_name":x.cut_name,"yield_rate":x.yield_rate,"extra_price_ht":x.extra_price_ht} for x in db.scalars(select(ProductCut)).all()],
        "clients":[{"id":x.id,"type":x.client_type,"name":x.name,"email":x.email,"active":x.active} for x in db.scalars(select(Client)).all()],
        "lots":[{"id":x.id,"product_id":x.product_id,"internal_lot":x.internal_lot,"supplier_lot":x.supplier_lot,"qty_received":x.qty_received,"qty_reserved":x.qty_reserved,"qty_consumed":x.qty_consumed,"qty_available":round(lot_available(x),3),"lot_stage":lot_stage(db,x.id),"expiry_date":x.expiry_date,"status":x.status} for x in db.scalars(select(Lot)).all()],
        "orders":[{"id":x.id,"client_id":x.client_id,"status":x.status,"delivery_mode":x.delivery_mode,"created_at":x.created_at} for x in db.scalars(select(Order)).all()],
        "order_lines":[{"id":x.id,"order_id":x.order_id,"product_id":x.product_id,"quantity":x.quantity,"unit_price_ht":x.unit_price_ht} for x in db.scalars(select(OrderLine)).all()],
        "production_jobs":[{"id":x.id,"product_id":x.product_id,"quantity_needed":x.quantity_needed,"status":x.status,"source_order_id":x.source_order_id,"created_at":x.created_at} for x in db.scalars(select(ProductionJob)).all()],
        "suppliers":[{"id":x.id,"name":x.name,"city":x.city,"specialty":x.specialty,"active":x.active} for x in db.scalars(select(Supplier)).all()],
        "purchase_orders":[{"id":x.id,"supplier_id":x.supplier_id,"status":x.status,"expected_date":x.expected_date,"note":x.note,"created_at":x.created_at} for x in db.scalars(select(PurchaseOrder)).all()],
        "invoices":[{"id":x.id,"order_id":x.order_id,"status":x.status,"amount_ht":x.amount_ht} for x in db.scalars(select(Invoice)).all()],
        "payments":[{"id":x.id,"order_id":x.order_id,"status":x.status,"method":x.method,"amount":x.amount,"reference":x.reference} for x in db.scalars(select(Payment)).all()],
        "equipment":[{"id":x.id,"name":x.name,"budget_low":x.budget_low,"budget_high":x.budget_high,"priority":x.priority,"status":x.status} for x in db.scalars(select(Equipment)).all()],
        "settings":[{"key":x.key,"value":x.value} for x in db.scalars(select(AppSetting)).all()],
        "general_sourcing_requests":[{"id":x.id,"requested_name":x.requested_name,"category":x.category,"quantity_text":x.quantity_text,"customer_email":x.customer_email,"note":x.note,"status":x.status,"created_at":x.created_at} for x in db.scalars(select(GeneralSourcingRequest)).all()],
        "integrity_snapshot":integrity_report(db)
    }
    audit(db,"BACKUP_EXPORT","full json snapshot 1.0.0"); db.commit()
    return JSONResponse(payload,headers={"Content-Disposition":"attachment; filename=LPFB-backup-1.0.0.json"})

@app.get("/manifest.webmanifest")
def manifest_file(): return FileResponse(BASE/"manifest.webmanifest",media_type="application/manifest+json")

@app.get("/service-worker.js")
def service_worker(): return FileResponse(BASE/"service-worker.js",media_type="application/javascript",headers={"Cache-Control":"no-cache"})

@app.get("/")
def root(): return FileResponse(BASE/"index.html")
