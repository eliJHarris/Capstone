from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os

app = FastAPI(title="Adviseme Core API")

# --- CORS (you can tighten origins in prod) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=False,  # set True only if you actually use cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Secrets helper: prefer file if present ---
def _read_secret(path: str, fallback: str = "") -> str:
    try:
        if path and os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return fallback

DB_HOST = os.getenv("DB_HOST", "adviseme-db")
DB_USER = os.getenv("DB_USER", "adviseme_app")
DB_NAME = os.getenv("DB_NAME", "adviseme")

DB_PASS = _read_secret(os.getenv("DB_PASS_FILE", ""), os.getenv("DB_PASS", "app_pass"))

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGO = "HS256"

# URL-encode in case the password has special characters
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}"

# Use pre_ping so dead connections get recycled
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

def verify_token(authorization: str = Header(...)):
    """Verify Bearer JWT token and return claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

@app.get("/")
def root():
    return {"message": "Core API online"}

@app.get("/health")
def health():
    # lightweight DB ping
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.get("/me")
def me(user=Depends(verify_token)):
    """Return JWT claims so the UI can show who is logged in."""
    return {"user": user}

@app.get("/db")
def test_db(user=Depends(verify_token)):
    """Confirm DB connection and return version."""
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT VERSION()")).scalar_one()
    return {"authenticated_user": user.get("sub"), "db_version": ver}
