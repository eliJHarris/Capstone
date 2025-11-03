#!/usr/bin/env bash
# scripts/bootstrap_ldap.sh
set -euo pipefail

########################
# ====== config ====== #
########################

LDAP_CONTAINER="${LDAP_CONTAINER:-adviseme-openldap}"
LDAP_URL="${LDAP_URL:-ldap://localhost:389}"

ADMIN_DN="${ADMIN_DN:-cn=admin,dc=adviseme,dc=local}"
ADMIN_PASS="${ADMIN_PASS:-admin_pass}"

VERBOSE="${VERBOSE:-1}"             # 1 = trace commands
BIND_TIMEOUT="${BIND_TIMEOUT:-120}" # seconds

# Users / DNs we'll insert
OU_BASE="dc=adviseme,dc=local"
PEOPLE_OU="ou=People,${OU_BASE}"
GROUPS_OU="ou=Groups,${OU_BASE}"
SERVICE_OU="ou=Service,${OU_BASE}"

ALICE_DN="cn=Alice Advisor,${PEOPLE_OU}"
ALICE_UID="aadvisor"
ALICE_PASS="AdvisorPass123!"

BOB_DN="cn=Bob Advisee,${PEOPLE_OU}"
BOB_UID="badvisee"
BOB_PASS="AdviseePass123!"

APP_DN="cn=adviseme-app,${SERVICE_OU}"
APP_PASS="AppBindPass123!"

ADVISORS_DN="cn=advisors,${GROUPS_OU}"
ADVISEES_DN="cn=advisees,${GROUPS_OU}"

#############################
# ===== pretty logs ======  #
#############################

RED="$(printf '\033[31m')"; GREEN="$(printf '\033[32m')"; YELLOW="$(printf '\033[33m')"
BLUE="$(printf '\033[34m')"; BOLD="$(printf '\033[1m')"; RESET="$(printf '\033[0m')"

log()  { echo -e "${BLUE}${BOLD}==>${RESET} $*"; }
ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}!${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✖${RESET} $*"; }

trap 'err "Failed on: ${BASH_COMMAND}"' ERR
[[ "$VERBOSE" == "1" ]] && set -x

#####################################
# ===== sudo precheck (nice) ====== #
#####################################

if ! sudo -n true 2>/dev/null; then
  err "This script uses sudo. Run it with: sudo $0"
  exit 1
fi

#########################################
# ===== helper: run ldapadd inline ==== #
#########################################

ldap_add_ldif () {
  # $1 = title (log label)
  log "$1"
  sudo docker exec -i "$LDAP_CONTAINER" ldapadd -x \
    -H "$LDAP_URL" \
    -D "$ADMIN_DN" \
    -w "$ADMIN_PASS"
  ok "$1 (applied)"
}

ldap_modify_ldif () {
  # $1 = title (log label)
  log "$1"
  sudo docker exec -i "$LDAP_CONTAINER" ldapmodify -x \
    -H "$LDAP_URL" \
    -D "$ADMIN_DN" \
    -w "$ADMIN_PASS"
  ok "$1 (applied)"
}

ldap_search () {
  # pass extra ldapsearch args after this function name
  sudo docker exec "$LDAP_CONTAINER" ldapsearch -LLL -x \
    -H "$LDAP_URL" \
    -D "$ADMIN_DN" \
    -w "$ADMIN_PASS" \
    "$@"
}

########################################
# ===== wait for LDAP to be ready ==== #
########################################

log "Using container: $LDAP_CONTAINER"
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | sed -n '1,20p'

log "Waiting for admin bind (timeout ${BIND_TIMEOUT}s)..."
START=$(date +%s)
while true; do
  if sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x \
      -H "$LDAP_URL" \
      -D "$ADMIN_DN" \
      -w "$ADMIN_PASS" >/dev/null 2>&1; then
    ok "Admin bind OK"
    break
  fi

  if [ $(( $(date +%s) - START )) -ge "$BIND_TIMEOUT" ]; then
    err "Timed out waiting for admin bind"
    exit 1
  fi
  sleep 2
done

log "namingContexts (one-shot)"
ldap_search -s base -b "" namingContexts || true

########################################
# ===== 1. Ensure OUs exist        ==== #
########################################

# We'll 'add' them unconditionally. If they already exist, ldapadd will error.
# That's fine; we'll just warn and keep going.
{
ldap_add_ldif "Create OUs (People, Groups, Service)" <<LDIF
dn: ${PEOPLE_OU}
objectClass: top
objectClass: organizationalUnit
ou: People

dn: ${GROUPS_OU}
objectClass: top
objectClass: organizationalUnit
ou: Groups

dn: ${SERVICE_OU}
objectClass: top
objectClass: organizationalUnit
ou: Service
LDIF
} || warn "Some OUs may already exist, continuing."

log "Validate Organizational Units"
ldap_search -b "$OU_BASE" "(objectClass=organizationalUnit)" dn ou

########################################
# ===== 2. Create groups           ==== #
########################################

{
ldap_add_ldif "Create groups (advisors, advisees)" <<LDIF
dn: ${ADVISORS_DN}
objectClass: top
objectClass: groupOfNames
cn: advisors
member: ${ADMIN_DN}

dn: ${ADVISEES_DN}
objectClass: top
objectClass: groupOfNames
cn: advisees
member: ${ADMIN_DN}
LDIF
} || warn "Groups may already exist, continuing."

log "Validate Groups"
ldap_search -b "$GROUPS_OU" "(cn=*)" dn cn member

########################################
# ===== 3. Create People + Service ==== #
########################################

{
ldap_add_ldif "Create people (Alice, Bob) and service account" <<LDIF
dn: ${ALICE_DN}
objectClass: inetOrgPerson
cn: Alice Advisor
sn: Advisor
givenName: Alice
uid: ${ALICE_UID}
mail: alice.advisor@adviseme.local
userPassword: ${ALICE_PASS}

dn: ${BOB_DN}
objectClass: inetOrgPerson
cn: Bob Advisee
sn: Advisee
givenName: Bob
uid: ${BOB_UID}
mail: bob.advisee@adviseme.local
userPassword: ${BOB_PASS}

dn: ${APP_DN}
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: adviseme-app
description: Application bind DN
userPassword: ${APP_PASS}
LDIF
} || warn "People/service may already exist, continuing."

log "Validate People"
ldap_search -b "$PEOPLE_OU" "(cn=*)" dn cn uid

log "Validate Service Account"
ldap_search -b "$SERVICE_OU" "(cn=adviseme-app)" dn cn

########################################
# ===== 4. Add people to groups    ==== #
########################################

{
ldap_modify_ldif "Add Alice to advisors; Bob to advisees" <<LDIF
dn: ${ADVISORS_DN}
changetype: modify
add: member
member: ${ALICE_DN}

dn: ${ADVISEES_DN}
changetype: modify
add: member
member: ${BOB_DN}
LDIF
} || warn "Group membership may already exist, continuing."

log "Validate Group memberships"
ldap_search -b "$GROUPS_OU" "(objectClass=groupOfNames)" dn cn member

########################################
# ===== 5. Test simple binds       ==== #
########################################

log "Test bind for Alice"
sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x \
  -H "$LDAP_URL" \
  -D "$ALICE_DN" \
  -w "$ALICE_PASS" >/dev/null && ok "Alice bind OK" || warn "Alice bind FAILED"

log "Test bind for Bob"
sudo docker exec "$LDAP_CONTAINER" ldapwhoami -x \
  -H "$LDAP_URL" \
  -D "$BOB_DN" \
  -w "$BOB_PASS" >/dev/null && ok "Bob bind OK" || warn "Bob bind FAILED"

########################################
# ===== 6. Snapshot tree           ==== #
########################################

log "Directory snapshot (DNs only)"
ldap_search -b "$OU_BASE" "(objectClass=*)" dn

ok "LDAP bootstrap completed successfully 🎉"
