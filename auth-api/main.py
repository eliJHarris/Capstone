import os
import ssl
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES, SUBTREE, Tls, BASE
from jose import jwt

app = FastAPI(title="Adviseme Auth API")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://localhost,https://localhost:5173,https://localhost:3000",
    ).split(",")
    if origin.strip()
]

ENABLE_CORS = os.getenv("ENABLE_CORS", "false").lower() == "true"

if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def _read_secret(env_name: str, default: str = "") -> str:
    """Allow *_FILE overrides for sensitive settings."""
    file_path = os.getenv(f"{env_name}_FILE", "")
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    return os.getenv(env_name, default)

LDAP_HOST       = os.getenv("LDAP_HOST", "adviseme-openldap")
LDAP_PORT       = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL    = os.getenv("LDAP_USE_SSL", "false").lower() == "true"
LDAP_TLS_VALIDATE = os.getenv("LDAP_TLS_VALIDATE", "false").lower() == "true"
LDAP_CA_CERT_FILE = os.getenv("LDAP_CA_CERT_FILE", "")

LDAP_BASE_DN    = os.getenv("LDAP_BASE_DN", "dc=adviseme,dc=local")

LDAP_PEOPLE_DN  = os.getenv("LDAP_PEOPLE_DN", "ou=People,dc=adviseme,dc=local")

ADVISOR_GROUP_DN = os.getenv("ADVISOR_GROUP_DN", f"cn=advisors,ou=Groups,{LDAP_BASE_DN}")
ADVISEE_GROUP_DN = os.getenv("ADVISEE_GROUP_DN", f"cn=advisees,ou=Groups,{LDAP_BASE_DN}")
DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE", "advisor")

LDAP_BIND_DN    = os.getenv("LDAP_BIND_DN", "cn=adviseme-app,ou=Service,dc=adviseme,dc=local")

LDAP_BIND_PASSWORD = (
    _read_secret("LDAP_BIND_PASSWORD") or
    os.getenv("LDAP_BIND_PW") or
    "AppBindPass123!"
)

JWT_SECRET      = _read_secret("JWT_SECRET", "change-me")
JWT_ALGO        = "HS256"
JWT_EXPIRE_MIN  = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

def _server():
    tls_config = None
    if LDAP_USE_SSL:
        if LDAP_TLS_VALIDATE and not LDAP_CA_CERT_FILE:
            raise RuntimeError("LDAP_TLS_VALIDATE is true but LDAP_CA_CERT_FILE is missing")
        tls_config = Tls(
            validate=ssl.CERT_REQUIRED if LDAP_TLS_VALIDATE else ssl.CERT_NONE,
            ca_certs_file=LDAP_CA_CERT_FILE or None,
        )
    return Server(
        LDAP_HOST,
        port=LDAP_PORT,
        use_ssl=LDAP_USE_SSL,
        tls=tls_config,
        get_info=ALL,
    )

def _bind_service() -> Connection:
    try:
        conn = Connection(
            _server(),
            user=LDAP_BIND_DN,
            password=LDAP_BIND_PASSWORD,
            auto_bind=True
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service bind failed: {e}")

def _find_user(username: str):
    """
    Use the service bind to locate the user's DN and some attrs.
    We search ONLY under LDAP_PEOPLE_DN instead of the domain root.
    """
    svc = _bind_service()
    try:
        search_filter = f"(|(uid={username})(cn={username}))"

        ok = svc.search(
            search_base=LDAP_PEOPLE_DN,    
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
        role = _resolve_role(svc, user_dn)

        return {
            "dn": user_dn,
            "cn": user_cn,
            "uid": user_uid,
            "mail": user_mail,
            "role": role,
        }
    finally:
        svc.unbind()

def _is_member(conn: Connection, group_dn: str, user_dn: str) -> bool:
    if not group_dn:
        return False
    try:
        ok = conn.search(
            search_base=group_dn,
            search_filter=f"(member={user_dn})",
            search_scope=BASE,
            attributes=["member"],
        )
        return bool(ok and conn.entries)
    except Exception:
        return False

def _resolve_role(conn: Connection, user_dn: str) -> str:
    if _is_member(conn, ADVISOR_GROUP_DN, user_dn):
        return "advisor"
    if _is_member(conn, ADVISEE_GROUP_DN, user_dn):
        return "advisee"
    return DEFAULT_USER_ROLE

def _verify_password(user_dn: str, password: str):
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
        "role": user_info.get("role", DEFAULT_USER_ROLE),
        "exp": now + timedelta(minutes=JWT_EXPIRE_MIN),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    user_info = _find_user(username)

    _verify_password(user_info["dn"], password)

    token = _issue_jwt(user_info)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "dn": user_info["dn"],
            "cn": user_info["cn"],
            "uid": user_info["uid"],
            "mail": user_info["mail"],
            "role": user_info.get("role", DEFAULT_USER_ROLE),
        },
    }

@app.get("/")
def root():
    return {"service": "auth-api", "status": "ok"}

@app.get("/health")
def health():
    _ = _bind_service()
    _.unbind()
    return {"status": "ok"}

@app.get("/debug/users")
def debug_users():
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
