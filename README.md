# Capstone (Docker Compose)

This repo contains two services (front-end and api). Use Docker Compose to build and run them in separate containers.

Prerequisites
- Docker (and Docker Compose plugin) installed on Linux.

Quick start
1. From the repository root (/home/user/Capstone) run:
   ```
   docker compose up --build -d
   ```
2. Front-end should be available at http://localhost:5173
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