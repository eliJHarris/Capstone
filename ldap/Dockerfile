# syntax=docker/dockerfile:1

FROM osixia/openldap:1.5.0

# Seed the directory tree with our bootstrap LDIF files.
COPY --chown=openldap:openldap bootstrap/ /container/service/slapd/assets/config/bootstrap/ldif/custom/

# Include TLS assets that are generated before docker build
COPY certs/ /container/service/slapd/assets/certs/
RUN chown -R openldap:openldap /container/service/slapd/assets/certs

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
