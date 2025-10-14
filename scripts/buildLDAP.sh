#!/usr/bin/env bash
set -e


LDAP_CONTAINER="adviseme-openldap"
ADMIN_DN="cn=admin,dc=adviseme,dc=local"
ADMIN_PASS="admin_pass"


until docker exec "$LDAP_CONTAINER" ldapsearch -x -H ldap://localhost:389 -s base -b "" namingContexts >/dev/null 2>&1; do
 sleep 2
done


docker exec -i "$LDAP_CONTAINER" ldapadd -x -H ldap://localhost:389 -D "$ADMIN_DN" -w "$ADMIN_PASS" <<'LDIF'
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


docker exec -i "$LDAP_CONTAINER" ldapadd -x -H ldap://localhost:389 -D "$ADMIN_DN" -w "$ADMIN_PASS" <<'LDIF'
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


docker exec -i "$LDAP_CONTAINER" ldapadd -x -H ldap://localhost:389 -D "$ADMIN_DN" -w "$ADMIN_PASS" <<'LDIF'
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


docker exec -i "$LDAP_CONTAINER" ldapmodify -x -H ldap://localhost:389 -D "$ADMIN_DN" -w "$ADMIN_PASS" <<'LDIF'
dn: cn=advisors,ou=Groups,dc=adviseme,dc=local
changetype: modify
add: member
member: cn=Alice Advisor,ou=People,dc=adviseme,dc=local


dn: cn=advisees,ou=Groups,dc=adviseme,dc=local
changetype: modify
add: member
member: cn=Bob Advisee,ou=People,dc=adviseme,dc=local
LDIF


docker exec "$LDAP_CONTAINER" ldapsearch -x -H ldap://localhost:389 -b "dc=adviseme,dc=local" "(objectClass=*)" dn