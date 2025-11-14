# Capstone (Docker Compose)

Use Docker Compose to build and run them in separate containers.

Prerequisites
- Docker (and Docker Compose plugin) installed on Linux. To install dependencies:
  ```
   sudo ./dockerSetup.sh
  ```
  

Quick start (may need to run following with ```sudo```)
1. Generate local secrets and certificates (self-signed, dev-only):
   ```
   ./ops/bootstrap-security.sh
   ```
   This script provisions DB/app passwords under `secrets/`, an HTTPS cert for the reverse proxy, and a private CA plus server cert for LDAP TLS.
2. From the repository root (/home/user/Capstone) run:
   ```
   docker compose up --build
   ```
3. Open https://localhost in your browser and accept the self-signed certificate warning the first time.
4. Auth API is proxied at https://localhost/auth and the core API at https://localhost/api (both require the HTTPS proxy to be running).

Local TLS & secrets
- Dev certificates are generated inside `reverse-proxy/certs/` (HTTPS) and `ldap/certs/` (LDAPS). Both directories are git-ignored: re-run `./ops/bootstrap-security.sh` whenever you need to recreate them.
- Import `reverse-proxy/certs/localhost.crt` into your OS/browser trust store to eliminate warnings. Likewise, import `ldap/certs/ldap-ca.crt` if you plan to interact with LDAP tools from the host.
- Application secrets live in `secrets/*.txt` and are also git-ignored. Remove any of them to force regeneration via the bootstrap script.
- If you rotate the LDAP certificates, rebuild the LDAP image so the new files are baked in: `docker compose build openldap`.
- The Vite dev server also serves over HTTPS; if the certificate files are available they are reused automatically so the browser trusts both the proxy and the dev server.
- Front-end code reads `VITE_AUTH_API_BASE_URL` to override the default `https://localhost/auth` target. Set it in a `.env` file when you need to hit a different host.

Stop and remove containers
```
docker compose down
```

Logs
- Follow combined logs:
  ```
  docker compose logs -f
  ```
- Follow only front-end logs:
  ```
  docker compose logs -f frontend
  ```
