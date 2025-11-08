from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import engine, get_db
from routes.schedules import router as schedules_router
from routes.pdf_scraper import router as pdf_scraper_router

# Initialize FastAPI app
app = FastAPI(
    title="AdviseMe API",
    description="Academic advising and scheduling platform API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schedules_router, prefix="/api")
app.include_router(pdf_scraper_router, prefix="/api")


# Health check endpoints
@app.get("/")
async def read_root():
    return {"message": "AdviseMe API is running", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/db")
def database_check():
    """Check database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            return {"status": "connected", "version": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": f"Error connecting to database: {e}"}
