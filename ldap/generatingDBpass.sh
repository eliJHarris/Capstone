#!/usr/bin/env bash

SECRETS_DIR="./secrets"
ROOT_PASS_FILE="$SECRETS_DIR/db_root_pass.txt"
APP_PASS_FILE="$SECRETS_DIR/dbapppass.txt"
LDAP_BIND_PASS_FILE="$SECRETS_DIR/ldap_bind_pass.txt"
JWT_SECRET_FILE="$SECRETS_DIR/jwt_secret.txt"
LDAP_ADMIN_PASS_FILE="$SECRETS_DIR/ldap_admin_pass.txt"

mkdir -p "$SECRETS_DIR"

generate_password() {
  openssl rand -base64 24 | tr -d '\n'
}

if [ ! -f "$ROOT_PASS_FILE" ]; then
  echo "Creating $ROOT_PASS_FILE..."
  generate_password > "$ROOT_PASS_FILE"
  chmod 600 "$ROOT_PASS_FILE"
else
  echo "$ROOT_PASS_FILE already exists — skipping."
fi

# Create app password if missing
if [ ! -f "$APP_PASS_FILE" ]; then
  echo "Creating $APP_PASS_FILE..."
  generate_password > "$APP_PASS_FILE"
  chmod 600 "$APP_PASS_FILE"
else
  echo "$APP_PASS_FILE already exists — skipping."
fi

# Create LDAP bind password if missing
if [ ! -f "$LDAP_BIND_PASS_FILE" ]; then
  echo "Creating $LDAP_BIND_PASS_FILE..."
  generate_password > "$LDAP_BIND_PASS_FILE"
  chmod 600 "$LDAP_BIND_PASS_FILE"
else
  echo "$LDAP_BIND_PASS_FILE already exists — skipping."
fi

# Ensure LDAP admin password file exists
if [ ! -f "$LDAP_ADMIN_PASS_FILE" ]; then
  echo "Creating $LDAP_ADMIN_PASS_FILE..."
  generate_password > "$LDAP_ADMIN_PASS_FILE"
  chmod 600 "$LDAP_ADMIN_PASS_FILE"
else
  echo "$LDAP_ADMIN_PASS_FILE already exists — skipping."
fi

# Create JWT secret if missing
if [ ! -f "$JWT_SECRET_FILE" ]; then
  echo "Creating $JWT_SECRET_FILE..."
  generate_password > "$JWT_SECRET_FILE"
  chmod 600 "$JWT_SECRET_FILE"
else
  echo "$JWT_SECRET_FILE already exists — skipping."
fi

echo
echo "Database secrets ready:"
ls -l "$SECRETS_DIR"

chown -R "$(id -u)":"$(id -g)" "$SECRETS_DIR"
