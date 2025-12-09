import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from db.database import engine
from dependencies.auth import require_user
from routes.schedules import router as schedules_router
from routes.pdf_scraper import router as pdf_scraper_router
from routes.notifications import router as notifications_router
from routes.users import router as users_router
from routes.openai import router as openai_router
from routes.advisors import router as advisors_router
from routes.degree_plans import router as degree_plans_router
from routes.degree_import import router as degree_import_router
from routes.advisees import router as advisees_router
from routes.terms import router as terms_router
from routes.transcripts import router as transcripts_router
from routes.emails import router as emails_router


app = FastAPI(
    title="AdviseMe API",
    description="Academic advising and scheduling platform API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

DEFAULT_ALLOWED = (
    "http://localhost,"
    "https://localhost,"
    "http://localhost:5173,"
    "https://localhost:5173,"
    "http://localhost:3000,"
    "https://localhost:3000,"
    "https://adviseme.local"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED).split(",")
    if origin.strip()
]

ENABLE_CORS = os.getenv("ENABLE_CORS", "false").lower() == "true"

if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=os.getenv(
            "ALLOWED_ORIGIN_REGEX",
            r"https?://.*",
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_ROUTERS = [
    schedules_router,
    pdf_scraper_router,
    notifications_router,
    users_router,
    openai_router,
    advisors_router,
    degree_plans_router,
    degree_import_router,
    advisees_router,
    terms_router,
    transcripts_router,
    emails_router,
]

for router in _ROUTERS:
    app.include_router(router, prefix="/api")
    app.include_router(router, include_in_schema=False)


@app.get("/")
async def read_root():
    return {"message": "AdviseMe API is running", "version": "1.0.0"}


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc: 
        return {"status": "degraded", "error": str(exc)}


@app.get("/db")
def database_check():
    """Check database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            return {"status": "connected", "version": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": f"Error connecting to database: {e}"}


@app.get("/me")
def me(user=Depends(require_user)):
    return {"user": user}
