# Capstone (Docker Compose)

Use Docker Compose to build and run them in separate containers.

Prerequisites
- Docker (and Docker Compose plugin) installed on Linux. To install dependencies:
  ```
   sudo ./dockerSetup.sh
  ```
  

Quick start (may need to run following with ```sudo```)
1. Generate local secrets and certificates (self-signed, dev-only).
   Every developer or deployment must create the password files under `secrets/`
   (`db_root_pass.txt`, `dbapppass.txt`, `ldap_admin_pass.txt`, `ldap_bind_pass.txt`, `jwt_secret.txt`)
   because they are git-ignored. You can either create them manually (one secret per file)
   or run the helper script:
   ```
   ./ops/bootstrap-security.sh
   ```
   This script provisions the password files, an HTTPS cert for the reverse proxy, and a private CA plus server cert for LDAP TLS.
2. From the repository root (/home/user/Capstone) run:
   ```
   docker compose up --build
   ```
2. Front-end should be available at http://localhost
3. API should be available at http://localhost:8000

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
