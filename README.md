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
