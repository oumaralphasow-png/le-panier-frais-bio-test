from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

BASE = Path(__file__).resolve().parent
DB = BASE / "lpfb.db"

app = FastAPI(title="Le Panier Frais Bio API", version="45.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@contextmanager
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    schema = (BASE / "schema.sql").read_text(encoding="utf-8")
    with db() as con:
        con.executescript(schema)

@app.on_event("startup")
def startup():
    init_db()

class OrderIn(BaseModel):
    client_type: str = "PRO"
    client_name: str
    product_id: int
    quantity: float = Field(gt=0)

@app.get("/health")
def health():
    with db() as con:
        con.execute("SELECT 1").fetchone()
    return {"status": "ok", "service": "Le Panier Frais Bio API", "version":"45.1"}

@app.get("/products")
def products():
    with db() as con:
        rows = con.execute("SELECT * FROM products ORDER BY name").fetchall()
        return [dict(r) for r in rows]

@app.get("/lots")
def lots():
    with db() as con:
        rows = con.execute("""
            SELECT l.*, p.reference, p.name,
                   ROUND(l.qty_received-l.qty_reserved-l.qty_consumed,3) AS qty_available
            FROM lots l JOIN products p ON p.id=l.product_id
            ORDER BY COALESCE(l.expiry_date,'9999-12-31'), l.id
        """).fetchall()
        return [dict(r) for r in rows]

@app.get("/orders")
def orders():
    with db() as con:
        rows = con.execute("""
            SELECT o.id,o.client_type,o.client_name,o.status,o.created_at,
                   ol.product_id,ol.quantity,p.name as product_name
            FROM orders o
            JOIN order_lines ol ON ol.order_id=o.id
            JOIN products p ON p.id=ol.product_id
            ORDER BY o.id DESC
        """).fetchall()
        return [dict(r) for r in rows]

@app.post("/orders")
def create_order(o: OrderIn):
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("""
            INSERT INTO orders(client_type,client_name,status,created_at)
            VALUES(?,?,?,?)
        """, (o.client_type,o.client_name,"CONFIRMEE",datetime.utcnow().isoformat()))
        order_id = cur.lastrowid
        con.execute("INSERT INTO order_lines(order_id,product_id,quantity) VALUES(?,?,?)",
                    (order_id,o.product_id,o.quantity))
        eligible = con.execute("""
            SELECT id, qty_received, qty_reserved, qty_consumed
            FROM lots
            WHERE product_id=? AND status='LIBERE'
            ORDER BY COALESCE(expiry_date,'9999-12-31'), id
        """,(o.product_id,)).fetchall()
        remaining = o.quantity
        allocations = []
        for lot in eligible:
            available = lot["qty_received"] - lot["qty_reserved"] - lot["qty_consumed"]
            take = min(remaining, max(0, available))
            if take > 0:
                con.execute("UPDATE lots SET qty_reserved=qty_reserved+? WHERE id=?", (take,lot["id"]))
                con.execute("INSERT INTO reservations(order_id,lot_id,quantity,status) VALUES(?,?,?,'ACTIVE')",
                            (order_id,lot["id"],take))
                allocations.append({"lot_id":lot["id"],"quantity":take})
                remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise HTTPException(409, detail={"code":"STOCK_INSUFFICIENT","requested":o.quantity,"missing":round(remaining,3)})
        con.execute("INSERT INTO audit_log(created_at,event_type,details) VALUES(?,?,?)",
                    (datetime.utcnow().isoformat(),"ORDER_CONFIRMED",f"order_id={order_id};qty={o.quantity}"))
        return {"order_id":order_id,"status":"CONFIRMEE","allocations":allocations}

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id:int):
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute("SELECT id,lot_id,quantity FROM reservations WHERE order_id=? AND status='ACTIVE'",
                           (order_id,)).fetchall()
        if not rows:
            raise HTTPException(404, "Aucune réservation active")
        for r in rows:
            con.execute("UPDATE lots SET qty_reserved=qty_reserved-? WHERE id=?", (r["quantity"],r["lot_id"]))
            con.execute("UPDATE reservations SET status='RELEASED' WHERE id=?", (r["id"],))
        con.execute("UPDATE orders SET status='ANNULEE' WHERE id=?", (order_id,))
        con.execute("INSERT INTO audit_log(created_at,event_type,details) VALUES(?,?,?)",
                    (datetime.utcnow().isoformat(),"ORDER_CANCELLED",f"order_id={order_id}"))
        return {"order_id":order_id,"status":"ANNULEE"}

@app.get("/audit")
def audit(limit:int=50):
    limit=max(1,min(limit,200))
    with db() as con:
        rows=con.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
        return [dict(r) for r in rows]

@app.get("/")
def home():
    return FileResponse(BASE/"index.html")
