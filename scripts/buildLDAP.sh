#!/usr/bin/env bash
# scripts/bootstrap_ldap.sh
set -euo pipefail

# ========= config =========
LDAP_CONTAINER="${LDAP_CONTAINER:-adviseme-openldap}"
LDAP_URL="${LDAP_URL:-ldap://localhost:389}"
ADMIN_DN="${ADMIN_DN:-cn=admin,dc=adviseme,dc=local}"
ADMIN_PASS="${ADMIN_PASS:-admin_pass}"
VERBOSE="${VERBOSE:-1}"            # 1 = trace commands
BIND_TIMEOUT="${BIND_TIMEOUT:-120}" # seconds

# ========= pretty logs =========
RED="$(printf '\033[31m')"; GREEN="$(printf '\033[32m')"; YELLOW="$(printf '\033[33m')"
BLUE="$(printf '\033[34m')"; BOLD="$(printf '\033[1m')"; RESET="$(printf '\033[0m')"
log()  { echo -e "${BLUE}${BOLD}==>${RESET} $*"; }
ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}!${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✖${RESET} $*"; }

trap 'err "Failed on: ${BASH_COMMAND}"' ERR
[[ "$VERBOSE" == "1" ]] && set -x

# Require sudo up front so loops don’t block on a password prompt
if ! sudo -n true 2>/dev/null; then
  err "This script uses sudo. Run it with: sudo $0"
  exit 1
fi

# ========= helpers =========
exec_ldif_add() {
  local title="$1"; shift
  log "$title"
  # Read LDIF from STDIN; write rejects inside container for visibility
  sudo docker exec -i "$LDAP_CONTAINER" sh -lc '
    set -e
    REJ="/tmp/ldapadd.rejects.ldif"
    rc=0
    ldapadd -S "$REJ" -c -x -H "'"$LDAP_URL"'" -D "'"$ADMIN_DN"'" -w "'"$ADMIN_PASS"'" || rc=$?
    if [ -s "$REJ" ]; then
      echo "---- Rejects ----"
      cat "$REJ"
      echo "-----------------"
    fi
    exit $rc
  '
  ok "$title (applied)"
}

exec_ldif_modify() {
  local title="$1"; shift
  log "$title"
  sudo docker exec -i "$LDAP_CONTAINER" ldapmodify -x -H "$LDAP_URL" -D "$ADMIN_DN" -w "$ADMIN_PASS" "$@"
  ok "$title (applied)"
}

validate() {
  local title="$1"; shift
  log "Validate: $title"
  sudo docker exec "$LDAP_CONTAINER" ldapsearch -LLL -x -H "$LDAP_URL" -D "$ADMIN_DN" -w "$ADMIN_PASS" "$@"
  ok "Validated: $title"
}

# ========= start =========
log "Using container: $LDAP_CONTAINER"
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | sed -n '1,10p'

# Readiness: wait for admin bind (most reliable), with timeout
log "Waiting for admin bind (timeout ${BIND_TIMEOUT}s)..."
START=$(date +%s)
while true; do
  if sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x -H "$LDAP_URL" -D "$ADMIN_DN" -w "$ADMIN_PASS" >/dev/null 2>&1; then
    ok "Admin bind OK"
    break
  fi
  if [ $(( $(date +%s) - START )) -ge "$BIND_TIMEOUT" ]; then
    err "Timed out waiting for admin bind"
    exit 1
  fi
  sleep 2
done

# Optional: show namingContexts once
log "namingContexts (one-shot)"
sudo docker exec "$LDAP_CONTAINER" ldapsearch -LLL -x -H "$LDAP_URL" -s base -b "" namingContexts || true

# 1) OUs
exec_ldif_add "Create OUs (People, Groups, Service)" <<'LDIF'
dn: ou=People,dc=adviseme,dc=local
objectClass: top
objectClass: organizationalUnit
ou: People

dn: ou=Groups,dc=adviseme,dc=local
objectClass: top
objectClass: organizationalUnit
ou: Groups

dn: ou=Service,dc=adviseme,dc=local
objectClass: top
objectClass: organizationalUnit
ou: Service
LDIF

validate "Organizational Units exist" -b "dc=adviseme,dc=local" "(objectClass=organizationalUnit)" dn ou

# 2) Groups
exec_ldif_add "Create groups (advisors, advisees)" <<'LDIF'
dn: cn=advisors,ou=Groups,dc=adviseme,dc=local
objectClass: top
objectClass: groupOfNames
cn: advisors
member: cn=admin,dc=adviseme,dc=local

dn: cn=advisees,ou=Groups,dc=adviseme,dc=local
objectClass: top
objectClass: groupOfNames
cn: advisees
member: cn=admin,dc=adviseme,dc=local
LDIF

validate "Groups exist" -b "ou=Groups,dc=adviseme,dc=local" "(cn=*)" dn cn

# 3) People + service account
exec_ldif_add "Create people (Alice, Bob) and service account" <<'LDIF'
dn: cn=Alice Advisor,ou=People,dc=adviseme,dc=local
objectClass: inetOrgPerson
cn: Alice Advisor
sn: Advisor
givenName: Alice
uid: aadvisor
mail: alice.advisor@adviseme.local
userPassword: AdvisorPass123!

dn: cn=Bob Advisee,ou=People,dc=adviseme,dc=local
objectClass: inetOrgPerson
cn: Bob Advisee
sn: Advisee
givenName: Bob
uid: badvisee
mail: bob.advisee@adviseme.local
userPassword: AdviseePass123!

dn: cn=adviseme-app,ou=Service,dc=adviseme,dc=local
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: adviseme-app
description: Application bind DN
userPassword: AppBindPass123!
LDIF

validate "People exist"   -b "ou=People,dc=adviseme,dc=local"  "(cn=*)" dn cn uid
validate "Service exists" -b "ou=Service,dc=adviseme,dc=local" "(cn=adviseme-app)" dn

# 4) Add people to groups
exec_ldif_modify "Add Alice to advisors; Bob to advisees" <<'LDIF'
dn: cn=advisors,ou=Groups,dc=adviseme,dc=local
changetype: modify
add: member
member: cn=Alice Advisor,ou=People,dc=adviseme,dc=local

dn: cn=advisees,ou=Groups,dc=adviseme,dc=local
changetype: modify
add: member
member: cn=Bob Advisee,ou=People,dc=adviseme,dc=local
LDIF

validate "Group memberships" -b "ou=Groups,dc=adviseme,dc=local" "(objectClass=groupOfNames)" dn member

# 5) Quick bind tests (whoami)
log "Test bind for Alice"
sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x -H "$LDAP_URL" \
  -D "cn=Alice Advisor,ou=People,dc=adviseme,dc=local" -w "AdvisorPass123!" >/dev/null
ok "Alice bind OK"

log "Test bind for Bob"
sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x -H "$LDAP_URL" \
  -D "cn=Bob Advisee,ou=People,dc=adviseme,dc=local" -w "AdviseePass123!" >/dev/null
ok "Bob bind OK"

# 6) Final tree snapshot (DNs only)
validate "Directory snapshot (DNs)" -b "dc=adviseme,dc=local" "(objectClass=*)" dn

ok "LDAP bootstrap completed successfully 🎉"
