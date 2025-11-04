# syntax=docker/dockerfile:1

FROM osixia/openldap:1.5.0

# Seed the directory tree with our bootstrap LDIF files.
COPY --chown=openldap:openldap bootstrap/ /container/service/slapd/assets/config/bootstrap/ldif/custom/

