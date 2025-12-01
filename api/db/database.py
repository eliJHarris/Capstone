import os
from typing import Generator, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _read_secret(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return None


DB_HOST = os.getenv("DB_HOST", "adviseme-db")
DB_USER = os.getenv("DB_USER", "adviseme_app")
DB_NAME = os.getenv("DB_NAME", "adviseme")

DB_PASS = os.getenv("DB_PASSWORD")
if not DB_PASS:
    DB_PASS = _read_secret(os.getenv("DB_PASSWORD_FILE")) or "app_pass"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
