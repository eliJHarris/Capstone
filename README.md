# Capstone (Docker Compose)

Use Docker Compose to build and run them in separate containers.

Prerequisites
- Docker (and Docker Compose plugin) installed on Linux. To install dependencies:
  ```
   sudo ./dockerSetup.sh
  ```
  

Quick start (may need to run following with ```sudo```)
1. Create a `.env` file with the required container secrets. Start from the sample and edit the values:
   ```
   cp .env.example .env
   ```
   Required keys: `DB_ROOT_PASSWORD`, `DB_APP_PASSWORD`, `LDAP_ADMIN_PASSWORD`, `JWT_SECRET`.
2. Generate local certificates (self-signed, dev-only) for the reverse proxy and LDAP:
   ```
   ./ops/bootstrap-security.sh
   ```
3. From the repository root (/home/user/Capstone) run:
   ```
   docker compose up --build
   ```
4. Front-end should be available at http://localhost
5. API should be available at http://localhost:8000

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

## OpenAI configuration

- Set an enviorment file for OpenAI API provided by team
