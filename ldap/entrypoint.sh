#!/bin/bash
set -euo pipefail
if [ -f /run/secrets/ldap_admin_pass ]; then
  export LDAP_ADMIN_PASSWORD="$(tr -d '\n' < /run/secrets/ldap_admin_pass)"
  export LDAP_CONFIG_PASSWORD="${LDAP_CONFIG_PASSWORD:-$LDAP_ADMIN_PASSWORD}"
fi
exec /container/tool/run "$@"
