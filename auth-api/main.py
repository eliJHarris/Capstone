import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Form, Depends
from pydantic import BaseModel
from ldap3 import Server, Connection, SUBTREE, ALL, Tls

app = FastAPI(title="Auth API (LDAP)")

# ---------- Config ----------
def _read_secret(path: Optional[str], fallback_env: Optional[str]) -> Optional[str]:
    """
    Read a secret from a file if path is set; otherwise return env var.
    Returns None if neither exists.
    """
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    if fallback_env:
        return os.getenv(fallback_env)
    return None

LDAP_HOST         = os.getenv("LDAP_HOST", "openldap")
LDAP_PORT         = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL      = os.getenv("LDAP_USE_SSL", "false").lower() in {"1", "true", "yes"}
LDAP_START_TLS    = os.getenv("LDAP_START_TLS", "false").lower() in {"1", "true", "yes"}

LDAP_BIND_DN      = os.getenv("LDAP_BIND_DN", "cn=adviseme-app,ou=Service,dc=adviseme,dc=local")
LDAP_BIND_PW      = _read_secret(os.getenv("LDAP_BIND_PASSWORD_FILE"), "LDAP_BIND_PASSWORD")

LDAP_BASE_DN      = os.getenv("LDAP_BASE_DN", "dc=adviseme,dc=local")
LDAP_PEOPLE_DN    = os.getenv("LDAP_PEOPLE_DN", "ou=People,dc=adviseme,dc=local")

# Search filter used to look up the user from a username
# We’ll search by uid OR mail OR cn
LDAP_USER_FILTER_TEMPLATE = os.getenv(
    "LDAP_USER_FILTER",
    "(|(uid={username})(mail={username})(cn={username}))"
)

# Optional: which attributes to return after we authenticate the user
USER_ATTRS = [a.strip() for a in os.getenv(
    "LDAP_USER_ATTRIBUTES",
    "cn,uid,mail"
).split(",") if a.strip()]

# ---------- LDAP helpers ----------
def make_server() -> Server:
    # You can customize TLS here if you enable LDAPS/StartTLS
    tls = Tls(validate=0) if (LDAP_USE_SSL or LDAP_START_TLS) else None
    return Server(LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_USE_SSL, get_info=ALL, tls=tls)

def bind_service(conn: Connection) -> None:
    if not LDAP_BIND_DN or not LDAP_BIND_PW:
        raise HTTPException(status_code=500, detail="Service bind not configured")
    if not conn.bind():
        # If using StartTLS:
        # if LDAP_START_TLS: conn.start_tls()
        if not conn.rebind(user=LDAP_BIND_DN, password=LDAP_BIND_PW):
            raise HTTPException(status_code=502, detail="LDAP service bind failed")

def find_user_dn(username: str) -> str:
    """
    Search LDAP under PEOPLE_DN using a broad filter and return the first entry_dn.
    """
    server = make_server()
    with Connection(server, user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=False) as conn:
        bind_service(conn)

        search_base = LDAP_PEOPLE_DN or LDAP_BASE_DN
        flt = LDAP_USER_FILTER_TEMPLATE.format(username=username)
        ok = conn.search(search_base, flt, search_scope=SUBTREE, attributes=["dn"])
        if not ok or len(conn.entries) == 0:
            raise HTTPException(status_code=401, detail="User not found")
        # Always use the DN returned by LDAP, do not construct a DN yourself
        return conn.entries[0].entry_dn

def verify_user_password(user_dn: str, password: str) -> None:
    """
    Verify the user's password by binding as that DN.
    """
    server = make_server()
    # Separate connection so we don't lose the admin bind/session
    with Connection(server, user=user_dn, password=password, auto_bind=False) as user_conn:
        if LDAP_START_TLS:
            try:
                user_conn.open()
                user_conn.start_tls()
            except Exception:
                pass
        if not user_conn.bind():
            # Invalid credentials → 401
            raise HTTPException(status_code=401, detail="Invalid credentials")

def fetch_user_attrs(user_dn: str) -> dict:
    """
    Re-bind as service and read attributes you want to return with the token/response.
    """
    server = make_server()
    with Connection(server, user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=False) as conn:
        bind_service(conn)
        ok = conn.search(user_dn, "(objectClass=*)", search_scope=SUBTREE, attributes=USER_ATTRS)
        if not ok or len(conn.entries) == 0:
            return {}
        entry = conn.entries[0]
        out = {"dn": entry.entry_dn}
        for attr in USER_ATTRS:
            try:
                out[attr] = entry[attr].value
            except Exception:
                pass
        return out

# ---------- Schemas ----------
class LoginJSON(BaseModel):
    username: str
    password: str

# ---------- Routes ----------
@app.get("/health")
def health():
    """
    Confirms we can bind as service/admin and read the base DN.
    """
    server = make_server()
    with Connection(server, user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=False) as conn:
        bind_service(conn)
        ok = conn.search(LDAP_BASE_DN, "(objectClass=*)", search_scope="BASE", attributes=["dn"])
        if not ok:
            raise HTTPException(status_code=502, detail="LDAP base search failed")
    return {"status": "ok", "ldap_host": LDAP_HOST, "base_dn": LDAP_BASE_DN}

@app.post("/login")
def login_form(username: str = Form(...), password: str = Form(...)):
    """
    Form-encoded login: use the user search, then bind exactly with entry_dn.
    """
    user_dn = find_user_dn(username)
    verify_user_password(user_dn, password)
    attrs = fetch_user_attrs(user_dn)
    # TODO: issue JWT here if you have a token layer; for now return basic info
    return {"message": "authenticated", "user": attrs or {"dn": user_dn}}

@app.post("/login/json")
def login_json(body: LoginJSON):
    user_dn = find_user_dn(body.username)
    verify_user_password(user_dn, body.password)
    attrs = fetch_user_attrs(user_dn)
    return {"message": "authenticated", "user": attrs or {"dn": user_dn}}
