import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES, SUBTREE
from jose import jwt

app = FastAPI(title="Adviseme Auth API")

# CORS so frontend (Vuetify or whatever) can call us locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # tighten later
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------ config from env -------------
LDAP_HOST       = os.getenv("LDAP_HOST", "adviseme-openldap")
LDAP_PORT       = int(os.getenv("LDAP_PORT", "389"))

# This is the ROOT of the directory (naming context)
LDAP_BASE_DN    = os.getenv("LDAP_BASE_DN", "dc=adviseme,dc=local")

# This is specifically where your users live
LDAP_PEOPLE_DN  = os.getenv("LDAP_PEOPLE_DN", "ou=People,dc=adviseme,dc=local")

# Service bind account (the "app account")
LDAP_BIND_DN    = os.getenv("LDAP_BIND_DN", "cn=adviseme-app,ou=Service,dc=adviseme,dc=local")

# IMPORTANT: normalize the password var name.
# We'll look for LDAP_BIND_PASSWORD first (what docker-compose typically sets),
# and fall back to LDAP_BIND_PW as a backup.
LDAP_BIND_PASSWORD = (
    os.getenv("LDAP_BIND_PASSWORD") or
    os.getenv("LDAP_BIND_PW") or
    "AppBindPass123!"
)

JWT_SECRET      = os.getenv("JWT_SECRET", "change-me")
JWT_ALGO        = "HS256"
JWT_EXPIRE_MIN  = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# ------------ helpers -------------
def _server():
    # get_info=ALL lets ldap3 cache schema, so you'll see those "cn=Subschema" queries in the logs
    return Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)

def _bind_service() -> Connection:
    """
    Bind as the service account to search LDAP.
    Returns an active ldap3 Connection object that you MUST close.
    """
    try:
        conn = Connection(
            _server(),
            user=LDAP_BIND_DN,
            password=LDAP_BIND_PASSWORD,
            auto_bind=True
        )
        return conn
    except Exception as e:
        # If we can't bind as service, the auth API is basically unusable
        raise HTTPException(status_code=500, detail=f"Service bind failed: {e}")

def _find_user(username: str):
    """
    Use the service bind to locate the user's DN and some attrs.
    We search ONLY under LDAP_PEOPLE_DN instead of the domain root.
    """
    svc = _bind_service()
    try:
        # match uid=aadvisor OR cn=aadvisor
        search_filter = f"(|(uid={username})(cn={username}))"

        ok = svc.search(
            search_base=LDAP_PEOPLE_DN,     # <-- key change here
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=ALL_ATTRIBUTES,
        )

        if not ok or len(svc.entries) == 0:
            raise HTTPException(status_code=401, detail="User not found")

        entry = svc.entries[0]
        user_dn  = entry.entry_dn
        user_cn  = str(getattr(entry, "cn", username))
        user_uid = str(getattr(entry, "uid", username))
        user_mail = str(getattr(entry, "mail", ""))

        return {
            "dn": user_dn,
            "cn": user_cn,
            "uid": user_uid,
            "mail": user_mail,
        }
    finally:
        svc.unbind()

def _verify_password(user_dn: str, password: str):
    """
    Try binding as the user with the supplied password.
    If bind fails -> invalid credentials.
    """
    try:
        with Connection(_server(), user=user_dn, password=password, auto_bind=True):
            return True
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

def _issue_jwt(user_info: dict) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_info["uid"] or user_info["cn"],
        "dn":  user_info["dn"],
        "cn":  user_info["cn"],
        "uid": user_info["uid"],
        "mail": user_info["mail"],
        "exp": now + timedelta(minutes=JWT_EXPIRE_MIN),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

# ------------ routes -------------
@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    # 1. find them in LDAP (by uid or cn)
    user_info = _find_user(username)

    # 2. bind-as-user to verify password
    _verify_password(user_info["dn"], password)

    # 3. issue JWT
    token = _issue_jwt(user_info)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "dn": user_info["dn"],
            "cn": user_info["cn"],
            "uid": user_info["uid"],
            "mail": user_info["mail"],
        },
    }

@app.get("/")
def root():
    return {"service": "auth-api", "status": "ok"}

@app.get("/health")
def health():
    # Super lightweight health: just prove service bind works
    _ = _bind_service()
    _.unbind()
    return {"status": "ok"}

@app.get("/debug/users")
def debug_users():
    # Show what the service account can SEE under ou=People
    svc = _bind_service()
    try:
        svc.search(
            search_base=LDAP_PEOPLE_DN,
            search_filter="(objectClass=inetOrgPerson)",
            search_scope=SUBTREE,
            attributes=["cn", "uid", "mail"]
        )
        return {
            "base": LDAP_PEOPLE_DN,
            "count": len(svc.entries),
            "dns":  [e.entry_dn for e in svc.entries],
            "uids": [str(getattr(e, "uid", "")) for e in svc.entries],
            "cns":  [str(getattr(e, "cn", "")) for e in svc.entries],
            "mails": [str(getattr(e, "mail", "")) for e in svc.entries],
        }
    finally:
        svc.unbind()
