# Capstone (Docker Compose)

Use Docker Compose to build and run them in separate containers.

Prerequisites
- Docker (and Docker Compose plugin) installed on Linux. To install dependencies:
  ```
   sudo ./dockerSetup.sh
  ```
  

Quick start (may need to run following with ```sudo```)
1. From the repository root (/home/user/Capstone) run:
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

## OpenAI configuration

- Set an `OPENAI_API_KEY` environment variable (or add it to a `.env` file in `api/`) before running the API container so the shared OpenAI service can authenticate.
- Optional environment variables: `OPENAI_DEFAULT_MODEL` (defaults to `gpt-4o-mini`) and `OPENAI_EMBEDDING_MODEL` (defaults to `text-embedding-3-large`).
- To use the client inside routes or services, import `get_openai_service` from `api.services.openai_service` and inject it via FastAPI `Depends`, then call `chat_completion(...)` or `create_embedding(...)` on the returned instance.
