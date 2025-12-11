FROM osixia/openldap:1.5.0

COPY --chown=openldap:openldap bootstrap/ /container/service/slapd/assets/config/bootstrap/ldif/custom/

COPY certs/ /container/service/slapd/assets/certs/
RUN chown -R openldap:openldap /container/service/slapd/assets/certs

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
