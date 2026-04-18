"""
database.py — PostgreSQL / Supabase configuration for the Veridian RSS backend.

Driver: psycopg2-binary (synchronous), matching the existing SQLAlchemy
        Session pattern used throughout all routers.

The .env file (server/.env) is loaded here before any other module reads
os.environ, because this module is imported first by main.py.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Load environment variables ────────────────────────────────────────────────
# Resolve to server/.env regardless of the working directory
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# —— Connection URL ——————————————————————————————————————————————————————
# Primary: PostgreSQL (Supabase) set in Hugging Face Secrets
# Fallback: local SQLite for dev
DATABASE_URL: str = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./db.sqlite3"
    print("[database] WARNING: DATABASE_URL not found, falling back to SQLite")
# Supabase/PostgreSQL fix: SQLAlchemy requires 'postgresql://' not 'postgres://'
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── SQLAlchemy engine ─────────────────────────────────────────────────────────
# pool_pre_ping=True — validates the connection before use, recovering
# automatically from Supabase idle-timeout disconnects.
if DATABASE_URL.startswith("sqlite"):
    # SQLite needs check_same_thread disabled for multi-threaded FastAPI
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """Yields a database session and guarantees it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
