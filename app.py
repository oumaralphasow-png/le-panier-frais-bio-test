
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE/'lpfb.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-IN-RENDER")
ALGORITHM = "HS256"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine: Engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args, pool_pre_ping=True)

app = FastAPI(title="Le Panier Frais Bio API", version="46.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # test uniquement
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at VARCHAR(40) NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY,
  created_at VARCHAR(40) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  details TEXT NOT NULL
);
"""

def db_execute(sql, params=None, fetch=False, fetchone=False):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        if fetchone:
            row = result.mappings().first()
            return dict(row) if row else None
        if fetch:
            return [dict(r) for r in result.mappings().all()]

def init_db():
    with engine.begin() as conn:
        for stmt in [s.strip() for s in SCHEMA.split(";") if s.strip()]:
            conn.execute(text(stmt))
    admin = db_execute("SELECT * FROM users WHERE email=:e", {"e":"admin@lpfb.test"}, fetchone=True)
    if not admin:
        db_execute(
            """INSERT INTO users(id,email,password_hash,full_name,role,active,created_at)
               VALUES(:id,:email,:ph,:fn,:role,1,:ca)""",
            {
                "id":1,
                "email":"admin@lpfb.test",
                "ph":pwd_context.hash("LPFB-Test-2026!"),
                "fn":"Administrateur Démo",
                "role":"ADMIN",
                "ca":datetime.now(timezone.utc).isoformat()
            }
        )

@app.on_event("startup")
def startup():
    init_db()

class LoginIn(BaseModel):
    email: str
    password: str

def create_token(user):
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Session invalide")
    user = db_execute("SELECT id,email,full_name,role,active FROM users WHERE id=:id", {"id":uid}, fetchone=True)
    if not user or not user["active"]:
        raise HTTPException(status_code=401, detail="Utilisateur inactif ou inconnu")
    return user

def require_roles(*roles):
    def guard(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Accès refusé pour ce rôle")
        return user
    return guard

@app.get("/health")
def health():
    db_execute("SELECT 1")
    return {"status":"ok","service":"Le Panier Frais Bio API","version":"46.0","database":"connected"}

@app.post("/auth/login")
def login(data: LoginIn):
    user = db_execute("SELECT * FROM users WHERE lower(email)=lower(:e)", {"e":data.email}, fetchone=True)
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    db_execute(
        "INSERT INTO audit_log(created_at,event_type,details) VALUES(:ca,:ev,:de)",
        {"ca":datetime.now(timezone.utc).isoformat(),"ev":"LOGIN_SUCCESS","de":f"user_id={user['id']};role={user['role']}"}
    )
    return {"access_token":create_token(user),"token_type":"bearer","role":user["role"],"name":user["full_name"]}

@app.get("/auth/me")
def me(user=Depends(current_user)):
    return user

@app.get("/admin/secure")
def admin_secure(user=Depends(require_roles("ADMIN","RESPONSABLE"))):
    return {"message":"Accès Admin autorisé","user":user}

@app.get("/production/secure")
def production_secure(user=Depends(require_roles("ADMIN","RESPONSABLE","PRODUCTION"))):
    return {"message":"Accès Production autorisé","user":user}

@app.get("/delivery/secure")
def delivery_secure(user=Depends(require_roles("ADMIN","RESPONSABLE","LIVRAISON"))):
    return {"message":"Accès Livraison autorisé","user":user}

@app.get("/audit")
def audit(user=Depends(require_roles("ADMIN","RESPONSABLE"))):
    return db_execute("SELECT * FROM audit_log ORDER BY id DESC", fetch=True)

@app.get("/")
def home():
    return FileResponse(BASE / "index.html")
