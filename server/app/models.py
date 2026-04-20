"""
models.py — SQLAlchemy ORM models for the Veridian Resume Screening System.

Changes from SQLite version:
  - Added `Vector(384)` embedding columns to JobPosting and Candidate.
    These store SBERT (all-MiniLM-L6-v2) 384-dimensional embeddings for
    pgvector cosine similarity search. Columns are nullable so existing rows
    migrated from SQLite remain valid; embeddings are backfilled on next run.
  - pgvector type is imported from `pgvector.sqlalchemy`.
"""

from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, deferred
import uuid
from .database import Base

import datetime


def generate_uuid():
    return str(uuid.uuid4())


# ── pgvector type ──────────────────────────────────────────────────────────────
# Import the Vector type only when connected to PostgreSQL.
# Falls back gracefully when running against the SQLite dev fallback.
try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_TYPE = Vector(384)   # all-MiniLM-L6-v2 produces 384-dim embeddings
except ImportError:
    # pgvector not installed or not needed (SQLite fallback) — store as Text
    from sqlalchemy import Text as Vector
    _VECTOR_TYPE = Text()


# ── Users ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=generate_uuid)
    employee_number = Column(String, unique=True, index=True, nullable=False)
    password_hash   = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    email           = Column(String, nullable=False)
    phone           = Column(String, nullable=True)
    company         = Column(String, nullable=True)
    location        = Column(String, nullable=True)
    avatar_color    = Column(String, nullable=True, default="#10b981")
    role            = Column(String, default="HR")          # 'Admin' | 'HR'
    is_active       = Column(Integer, default=1)            # 1 = active, 0 = deactivated
    force_reset     = Column(Integer, default=0)            # 1 = must reset on next login
    created_at      = Column(
        String, nullable=False,
        default=lambda: datetime.datetime.utcnow().isoformat()
    )


# ── Job Postings ───────────────────────────────────────────────────────────────
class JobPosting(Base):
    __tablename__ = "jobs"

    id                  = Column(String, primary_key=True, default=generate_uuid)
    title               = Column(String, nullable=False)
    department          = Column(String, nullable=False)
    location            = Column(String, nullable=False)
    type                = Column(String, nullable=False)
    status              = Column(String, default="Active")  # 'Active' | 'Draft' | 'Closed'
    applicantsCount     = Column(Integer, default=0)
    postedDate          = Column(String, nullable=False)
    description         = Column(Text, nullable=True)
    requirements        = Column(Text, nullable=True)       # JSON string
    salary              = Column(String, nullable=True)
    parsedRequirements  = Column(Text, nullable=True)       # JSON string array
    created_by_id       = Column(String, ForeignKey("users.id"), nullable=True)

    # SBERT embedding of the full job description + requirements text.
    # Used by pgvector to rank candidates by semantic similarity.
    embedding           = deferred(Column(_VECTOR_TYPE, nullable=True))

    candidates = relationship("Candidate", back_populates="job")


# ── Candidates ─────────────────────────────────────────────────────────────────
class Candidate(Base):
    __tablename__ = "candidates"

    id                = Column(String, primary_key=True, default=generate_uuid)
    name              = Column(String, nullable=False)
    email             = Column(String, nullable=False)
    phone             = Column(String, nullable=True)
    applied_job_id    = Column(String, ForeignKey("jobs.id"), nullable=True, index=True)
    probability_score = Column(Float, nullable=False)
    gyr_tier          = Column(String, nullable=False, index=True)  # 'Green' | 'Yellow' | 'Red'
    status            = Column(String, default="Pending", index=True)
    resume_url        = Column(String, nullable=True)
    appliedDate       = Column(String, nullable=False)

    # SBERT embedding of the resume text.
    # Null for rows migrated from SQLite; populated on new submissions.
    embedding         = deferred(Column(_VECTOR_TYPE, nullable=True))

    job = relationship("JobPosting", back_populates="candidates")


# ── Activity Logs ──────────────────────────────────────────────────────────────
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id          = Column(String, primary_key=True, default=generate_uuid)
    user_id     = Column(String, nullable=True)
    action_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    timestamp   = Column(
        String, nullable=False,
        default=lambda: datetime.datetime.utcnow().isoformat()
    )
