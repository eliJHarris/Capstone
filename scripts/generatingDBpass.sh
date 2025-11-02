#!/usr/bin/env bash
set -euo pipefail

SECRETS_DIR="./secrets"
ROOT_PASS_FILE="$SECRETS_DIR/db_root_pass.txt"
APP_PASS_FILE="$SECRETS_DIR/dbapppass.txt"

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

echo
echo "Database secrets ready:"
ls -l "$SECRETS_DIR"
