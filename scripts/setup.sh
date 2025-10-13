#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here"

mkdir -p secrets
gen() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32; echo; }
[ ! -s secrets/db_root_pass.txt ] && gen > secrets/db_root_pass.txt
[ ! -s secrets/dbapppass.txt ]    && gen > secrets/dbapppass.txt
[ ! -s secrets/ldap_admin_pass.txt ] && gen > secrets/ldap_admin_pass.txt
chmod 600 secrets/*.txt

mkdir -p certs
if [ ! -s certs/ldap.key ] || [ ! -s certs/ldap.crt ]; then
  openssl req -x509 -newkey rsa:4096 -nodes -days 825 \
    -subj "/CN=localhost" \
    -keyout certs/ldap.key -out certs/ldap.crt
  cp certs/ldap.crt certs/ca.crt
  chmod 600 certs/ldap.key
  chmod 644 certs/ldap.crt certs/ca.crt
fi

docker compose config >/dev/null
docker compose up -d
sleep 5
docker inspect --format='{{.Name}} {{.State.Health.Status}}' $(docker compose ps -q) || true

