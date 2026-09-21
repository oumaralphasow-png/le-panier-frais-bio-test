import os, json
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

BASE = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE/'lpfb.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-IN-RENDER")
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

class Delivery(Base):
    __tablename__="deliveries"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    status: Mapped[str]=mapped_column(String(30),default="A_PREPARER")
    slot: Mapped[Optional[str]]=mapped_column(String(100),nullable=True)

class Invoice(Base):
    __tablename__="invoices"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id"))
    status: Mapped[str]=mapped_column(String(30),default="BROUILLON")
    amount_ht: Mapped[float]=mapped_column(Float,default=0)

class Supplier(Base):
    __tablename__="suppliers"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str]=mapped_column(String(255),unique=True)
    city: Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    specialty: Mapped[Optional[str]]=mapped_column(String(500),nullable=True)
    active: Mapped[int]=mapped_column(Integer,default=1)

class Equipment(Base):
    __tablename__="equipment"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str]=mapped_column(String(255))
    budget_low: Mapped[float]=mapped_column(Float,default=0)
    budget_high: Mapped[float]=mapped_column(Float,default=0)
    priority: Mapped[str]=mapped_column(String(40),default="INDISPENSABLE")
    status: Mapped[str]=mapped_column(String(40),default="A_ACHETER")

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

app=FastAPI(title="Le Panier Frais Bio API",version="50.0-final")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth=OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def audit(db,event,details):
    db.add(AuditLog(created_at=datetime.now(timezone.utc).isoformat(),event_type=event,details=details))

def setting(db,key,default=""):
    row=db.scalar(select(AppSetting).where(AppSetting.key==key)); return row.value if row else default

def seed():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(func.lower(User.email)=="admin@lpfb.test")):
            db.add(User(email="admin@lpfb.test",password_hash=pwd.hash("LPFB-Test-2026!"),full_name="Administrateur Le Panier Frais Bio",role="ADMIN",active=1,created_at=datetime.now(timezone.utc).isoformat()))
        if not db.scalar(select(Client).where(Client.name=="Restaurant Démo")):
            db.add_all([Client(client_type="PRO",name="Restaurant Démo",email="pro@example.test"),Client(client_type="B2C",name="Client Démo",email="client@example.test")])
        if not db.scalar(select(Product).where(Product.reference=="LPFB-CAR-001")):
            carrot=Product(reference="LPFB-CAR-001",name="Carottes bio",family="Légumes préparés",unit="kg",price_ht=6.90,active=1)
            green=Product(reference="LPFB-GRN-033",name="THE GREEN 33 cl",family="Jus",unit="bouteille",price_ht=4.50,active=1)
            salad=Product(reference="LPFB-SAL-JUS",name="Formule salade + jus",family="Formules",unit="formule",price_ht=6.36,active=1)
            db.add_all([carrot,green,salad]); db.flush()
            db.add_all([ProductCut(product_id=carrot.id,cut_name=x,yield_rate=y,extra_price_ht=e) for x,y,e in [("Rondelles",.88,.30),("Bâtonnets",.86,.40),("Julienne",.84,.50),("Dés",.85,.45),("Râpée",.90,.35)]])
            db.add_all([
                Lot(product_id=carrot.id,internal_lot="CAR-A12",supplier_lot="FOUR-2026-A",qty_received=25,expiry_date="2026-09-22",status="LIBERE"),
                Lot(product_id=carrot.id,internal_lot="CAR-A13",supplier_lot="FOUR-2026-B",qty_received=35,expiry_date="2026-09-25",status="LIBERE"),
                Lot(product_id=carrot.id,internal_lot="CAR-X99",supplier_lot="FOUR-2026-X",qty_received=12,expiry_date="2026-09-21",status="BLOQUE")])
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
        defaults={"company_name":"Le Panier Frais Bio","store_area_m2":"29","investment_budget":"40000","social_formula":"Salade + jus : 7 €","click_collect":"Actif"}
        for k,v in defaults.items():
            if not db.scalar(select(AppSetting).where(AppSetting.key==k)): db.add(AppSetting(key=k,value=v))
        db.commit()

@app.on_event("startup")
def startup(): seed()

class LoginIn(BaseModel): email:str; password:str
class ClientIn(BaseModel): client_type:str; name:str; email:Optional[str]=None
class ProductIn(BaseModel): reference:str; name:str; family:str="Fruits & légumes"; unit:str="kg"; price_ht:float=Field(ge=0)
class LotIn(BaseModel): product_id:int; internal_lot:str; supplier_lot:Optional[str]=None; qty_received:float=Field(gt=0); expiry_date:Optional[str]=None; status:str="LIBERE"
class OrderIn(BaseModel): client_id:int; product_id:int; quantity:float=Field(gt=0); delivery_mode:str="LIVRAISON"; cut_name:Optional[str]=None; note:Optional[str]=None
class ProductionIn(BaseModel): product_id:int; quantity_needed:float=Field(gt=0); source_order_id:Optional[int]=None
class SupplierIn(BaseModel): name:str; city:Optional[str]=None; specialty:Optional[str]=None
class EquipmentIn(BaseModel): name:str; budget_low:float=0; budget_high:float=0; priority:str="INDISPENSABLE"; status:str="A_ACHETER"
class SettingIn(BaseModel): value:str

def make_token(user):
    return jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET_KEY,algorithm="HS256")

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

@app.get("/health")
def health(db:Session=Depends(get_db)):
    db.execute(select(1)); return {"status":"ok","version":"50.0-final","database":"postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite"}

@app.post("/auth/login")
def login(data:LoginIn,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(func.lower(User.email)==data.email.lower()))
    if not user or not pwd.verify(data.password,user.password_hash): raise HTTPException(401,"Identifiants incorrects")
    audit(db,"LOGIN_SUCCESS",f"user_id={user.id};role={user.role}"); db.commit()
    return {"access_token":make_token(user),"token_type":"bearer","name":user.full_name,"role":user.role}

@app.get("/auth/me")
def me(user=Depends(current_user)): return {"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role}

@app.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user=Depends(current_user)):
    stock=sum(max(0,l.qty_received-l.qty_reserved-l.qty_consumed) for l in db.scalars(select(Lot).where(Lot.status=="LIBERE")).all())
    lots=db.scalars(select(Lot)).all(); today=date.today()
    expiring=0
    for l in lots:
        if l.expiry_date:
            try:
                d=date.fromisoformat(l.expiry_date)
                if 0 <= (d-today).days <= 3: expiring += 1
            except: pass
    return {"products":db.scalar(select(func.count(Product.id))) or 0,"clients":db.scalar(select(func.count(Client.id))) or 0,"orders":db.scalar(select(func.count(Order.id))) or 0,"stock_available":round(stock,2),"production_open":db.scalar(select(func.count(ProductionJob.id)).where(ProductionJob.status!="TERMINE")) or 0,"expiring_lots":expiring,"blocked_lots":db.scalar(select(func.count(Lot.id)).where(Lot.status=="BLOQUE")) or 0,"equipment_budget_low":round(sum(x.budget_low for x in db.scalars(select(Equipment)).all()),2),"equipment_budget_high":round(sum(x.budget_high for x in db.scalars(select(Equipment)).all()),2)}

@app.get("/clients")
def clients(db:Session=Depends(get_db),user=Depends(current_user)): return [{"id":x.id,"client_type":x.client_type,"name":x.name,"email":x.email,"active":x.active} for x in db.scalars(select(Client).order_by(Client.name)).all()]
@app.post("/clients")
def create_client(data:ClientIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","VENTE"))):
    row=Client(**data.model_dump()); db.add(row); audit(db,"CLIENT_CREATE",data.name); db.commit(); db.refresh(row); return {"id":row.id}

@app.get("/products")
def products(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    for p in db.scalars(select(Product).order_by(Product.name)).all():
        cuts=[{"name":c.cut_name,"yield_rate":c.yield_rate,"extra_price_ht":c.extra_price_ht} for c in db.scalars(select(ProductCut).where(ProductCut.product_id==p.id)).all()]
        out.append({"id":p.id,"reference":p.reference,"name":p.name,"family":p.family,"unit":p.unit,"price_ht":p.price_ht,"active":p.active,"cuts":cuts})
    return out
@app.post("/products")
def create_product(data:ProductIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if db.scalar(select(Product).where(Product.reference==data.reference)): raise HTTPException(409,"Référence déjà utilisée")
    p=Product(**data.model_dump()); db.add(p); audit(db,"PRODUCT_CREATE",data.reference); db.commit(); db.refresh(p); return {"id":p.id}

@app.get("/lots")
def lots(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    for x in db.scalars(select(Lot).order_by(Lot.expiry_date)).all():
        out.append({"id":x.id,"product_id":x.product_id,"product_name":x.product.name,"internal_lot":x.internal_lot,"supplier_lot":x.supplier_lot,"qty_received":x.qty_received,"qty_reserved":x.qty_reserved,"qty_consumed":x.qty_consumed,"qty_available":round(max(0,x.qty_received-x.qty_reserved-x.qty_consumed),3),"expiry_date":x.expiry_date,"status":x.status})
    return out
@app.post("/lots")
def create_lot(data:LotIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","STOCK"))):
    if not db.get(Product,data.product_id): raise HTTPException(404,"Produit introuvable")
    if db.scalar(select(Lot).where(Lot.internal_lot==data.internal_lot)): raise HTTPException(409,"Lot déjà existant")
    x=Lot(**data.model_dump()); db.add(x); audit(db,"LOT_RECEIPT",data.internal_lot); db.commit(); db.refresh(x); return {"id":x.id}

@app.get("/orders")
def orders(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    for o in db.scalars(select(Order).order_by(Order.id.desc())).all():
        line=db.scalar(select(OrderLine).where(OrderLine.order_id==o.id)); opt=db.scalar(select(OrderOption).where(OrderOption.order_id==o.id))
        out.append({"id":o.id,"client_name":o.client.name,"client_type":o.client.client_type,"status":o.status,"delivery_mode":o.delivery_mode,"created_at":o.created_at,"product_name":line.product.name if line else "—","quantity":line.quantity if line else 0,"amount_ht":round((line.quantity*line.unit_price_ht) if line else 0,2),"cut_name":opt.cut_name if opt else None,"note":opt.note if opt else None})
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
    remaining=data.quantity
    lotsq=db.scalars(select(Lot).where(Lot.product_id==product.id,Lot.status=="LIBERE").order_by(Lot.expiry_date.asc())).all()
    for lot in lotsq:
        available=max(0,lot.qty_received-lot.qty_reserved-lot.qty_consumed)
        take=min(remaining,available)
        if take>0:
            lot.qty_reserved += take; db.add(Reservation(order_id=order.id,lot_id=lot.id,quantity=take,status="ACTIVE")); remaining -= take
        if remaining<=0: break
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
    if o.status=="ANNULEE": return {"status":"ANNULEE"}
    for r in db.scalars(select(Reservation).where(Reservation.order_id==order_id,Reservation.status=="ACTIVE")).all():
        lot=db.get(Lot,r.lot_id); lot.qty_reserved=max(0,lot.qty_reserved-r.quantity); r.status="ANNULEE"
    o.status="ANNULEE"; audit(db,"ORDER_CANCEL",f"order_id={order_id}"); db.commit(); return {"status":o.status}

@app.get("/production")
def production(db:Session=Depends(get_db),user=Depends(current_user)):
    return [{"id":x.id,"product_name":x.product.name,"quantity_needed":x.quantity_needed,"status":x.status,"source_order_id":x.source_order_id,"created_at":x.created_at} for x in db.scalars(select(ProductionJob).order_by(ProductionJob.id.desc())).all()]
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
def deliveries(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    for d in db.scalars(select(Delivery).order_by(Delivery.id.desc())).all():
        o=db.get(Order,d.order_id); out.append({"id":d.id,"order_id":d.order_id,"client_name":o.client.name if o else "—","mode":o.delivery_mode if o else "—","status":d.status,"slot":d.slot})
    return out
@app.post("/deliveries/{delivery_id}/advance")
def advance_delivery(delivery_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","LIVRAISON"))):
    d=db.get(Delivery,delivery_id)
    if not d: raise HTTPException(404,"Livraison introuvable")
    seq=["A_PREPARER","PRETE","EN_COURS","LIVREE"] if (db.get(Order,d.order_id).delivery_mode=="LIVRAISON") else ["A_PREPARER","PRETE","RETIRÉE"]
    d.status=seq[min(seq.index(d.status)+1,len(seq)-1)] if d.status in seq else seq[0]; audit(db,"DELIVERY_ADVANCE",f"delivery_id={delivery_id};status={d.status}"); db.commit(); return {"status":d.status}

@app.get("/invoices")
def invoices(db:Session=Depends(get_db),user=Depends(current_user)):
    out=[]
    for i in db.scalars(select(Invoice).order_by(Invoice.id.desc())).all():
        o=db.get(Order,i.order_id); out.append({"id":i.id,"order_id":i.order_id,"client_name":o.client.name if o else "—","amount_ht":round(i.amount_ht,2),"status":i.status})
    return out
@app.post("/invoices/{invoice_id}/validate")
def validate_invoice(invoice_id:int,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER","COMPTA"))):
    i=db.get(Invoice,invoice_id)
    if not i: raise HTTPException(404,"Facture introuvable")
    i.status="VALIDEE"; audit(db,"INVOICE_VALIDATE",f"invoice_id={invoice_id}"); db.commit(); return {"status":i.status}

@app.get("/suppliers")
def suppliers(db:Session=Depends(get_db),user=Depends(current_user)): return [{"id":x.id,"name":x.name,"city":x.city,"specialty":x.specialty,"active":x.active} for x in db.scalars(select(Supplier).order_by(Supplier.name)).all()]
@app.post("/suppliers")
def create_supplier(data:SupplierIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    if db.scalar(select(Supplier).where(Supplier.name==data.name)): raise HTTPException(409,"Fournisseur déjà existant")
    x=Supplier(**data.model_dump()); db.add(x); audit(db,"SUPPLIER_CREATE",data.name); db.commit(); db.refresh(x); return {"id":x.id}

@app.get("/equipment")
def equipment(db:Session=Depends(get_db),user=Depends(current_user)): return [{"id":x.id,"name":x.name,"budget_low":x.budget_low,"budget_high":x.budget_high,"priority":x.priority,"status":x.status} for x in db.scalars(select(Equipment).order_by(Equipment.id)).all()]
@app.post("/equipment")
def create_equipment(data:EquipmentIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))):
    x=Equipment(**data.model_dump()); db.add(x); audit(db,"EQUIPMENT_CREATE",data.name); db.commit(); db.refresh(x); return {"id":x.id}

@app.get("/settings")
def settings(db:Session=Depends(get_db),user=Depends(current_user)): return {x.key:x.value for x in db.scalars(select(AppSetting)).all()}
@app.put("/settings/{key}")
def update_setting(key:str,data:SettingIn,db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    x=db.scalar(select(AppSetting).where(AppSetting.key==key))
    if not x: x=AppSetting(key=key,value=data.value); db.add(x)
    else: x.value=data.value
    audit(db,"SETTING_UPDATE",f"{key}={data.value}"); db.commit(); return {"key":key,"value":data.value}

@app.get("/audit")
def audit_log(db:Session=Depends(get_db),user=Depends(roles("ADMIN","MANAGER"))): return [{"created_at":x.created_at,"event_type":x.event_type,"details":x.details} for x in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()]

@app.get("/backup")
def backup(db:Session=Depends(get_db),user=Depends(roles("ADMIN"))):
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"products":[{"reference":x.reference,"name":x.name,"price_ht":x.price_ht} for x in db.scalars(select(Product)).all()],"clients":[{"type":x.client_type,"name":x.name,"email":x.email} for x in db.scalars(select(Client)).all()],"suppliers":[{"name":x.name,"city":x.city,"specialty":x.specialty} for x in db.scalars(select(Supplier)).all()],"equipment":[{"name":x.name,"budget_low":x.budget_low,"budget_high":x.budget_high,"status":x.status} for x in db.scalars(select(Equipment)).all()]}
    audit(db,"BACKUP_EXPORT","json snapshot"); db.commit(); return JSONResponse(payload,headers={"Content-Disposition":"attachment; filename=lpfb-backup.json"})

@app.get("/")
def root(): return FileResponse(BASE/"index.html")
