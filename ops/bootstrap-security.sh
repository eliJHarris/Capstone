#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CERTS_DIR="$ROOT_DIR/reverse-proxy/certs"
LDAP_CERTS_DIR="$ROOT_DIR/ldap/certs"
SECRETS_SCRIPT="$ROOT_DIR/ldap/generatingDBpass.sh"

# ========================
# NGINX / HTTPS CERT
# ========================
mkdir -p "$CERTS_DIR"
if [ ! -f "$CERTS_DIR/localhost.crt" ] || [ ! -f "$CERTS_DIR/localhost.key" ]; then
  echo "Generating HTTPS certificate for reverse proxy..."
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "$CERTS_DIR/localhost.key" -out "$CERTS_DIR/localhost.crt" \
    -subj "/CN=localhost" >/dev/null 2>&1
  chmod 600 "$CERTS_DIR/localhost.key"
else
  echo "Reverse proxy certificate already exists — skipping."
fi

# ========================
# LDAP CA + SERVER CERT
# ========================
mkdir -p "$LDAP_CERTS_DIR"
if [ ! -f "$LDAP_CERTS_DIR/ldap-ca.crt" ]; then
  echo "Generating LDAP CA..."
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "$LDAP_CERTS_DIR/ldap-ca.key" -out "$LDAP_CERTS_DIR/ldap-ca.crt" \
    -subj "/CN=Adviseme LDAP CA" >/dev/null 2>&1
else
  echo "LDAP CA already exists — skipping."
fi

# OpenLDAP image expects ca.crt in its certs directory
cp "$LDAP_CERTS_DIR/ldap-ca.crt" "$LDAP_CERTS_DIR/ca.crt"
cp "$LDAP_CERTS_DIR/ldap-ca.key" "$LDAP_CERTS_DIR/ca.key"
chmod 600 "$LDAP_CERTS_DIR"/ldap-ca.key "$LDAP_CERTS_DIR"/ca.key

if [ ! -f "$LDAP_CERTS_DIR/ldap-server.crt" ]; then
  echo "Generating LDAP server certificate..."
  openssl req -new -nodes -newkey rsa:2048 \
    -keyout "$LDAP_CERTS_DIR/ldap-server.key" -out "$LDAP_CERTS_DIR/ldap-server.csr" \
    -subj "/CN=adviseme-openldap" >/dev/null 2>&1

  cat <<'EXT' > "$LDAP_CERTS_DIR/ldap-server.ext"
subjectAltName=DNS:adviseme-openldap,DNS:localhost
extendedKeyUsage=serverAuth
EXT

  openssl x509 -req -in "$LDAP_CERTS_DIR/ldap-server.csr" \
    -CA "$LDAP_CERTS_DIR/ldap-ca.crt" -CAkey "$LDAP_CERTS_DIR/ldap-ca.key" -CAcreateserial \
    -out "$LDAP_CERTS_DIR/ldap-server.crt" -days 825 -sha256 \
    -extfile "$LDAP_CERTS_DIR/ldap-server.ext" >/dev/null 2>&1
else
  echo "LDAP server certificate already exists — skipping."
fi

# OpenLDAP image expects ldap.crt / ldap.key in its certs directory
cp "$LDAP_CERTS_DIR/ldap-server.crt" "$LDAP_CERTS_DIR/ldap.crt"
cp "$LDAP_CERTS_DIR/ldap-server.key" "$LDAP_CERTS_DIR/ldap.key"
chmod 600 "$LDAP_CERTS_DIR"/ldap-server.key "$LDAP_CERTS_DIR"/ldap.key

rm -f "$LDAP_CERTS_DIR/ldap-server.csr" "$LDAP_CERTS_DIR/ldap-server.ext" "$LDAP_CERTS_DIR/ldap-ca.srl" 2>/dev/null || true

chown -R "$(id -u)":"$(id -g)" "$LDAP_CERTS_DIR"

# ========================
# APP SECRETS
# ========================
if [ -x "$SECRETS_SCRIPT" ]; then
  echo "Ensuring application secrets exist..."
  (cd "$ROOT_DIR" && bash "$SECRETS_SCRIPT")
else
  echo "Warning: secrets script $SECRETS_SCRIPT not found or not executable" >&2
fi

echo "Security assets are ready."
