"""
vector_search.py — pgvector cosine similarity search helpers.

Provides functions to:
  1. Rank candidates for a given job using the pgvector <=> (cosine distance)
     operator directly in PostgreSQL — far more efficient than loading all
     embeddings into Python for in-memory comparison.
  2. Find jobs similar to a given embedding (reverse lookup).

The <=> operator returns cosine DISTANCE (0 = identical, 2 = opposite).
We convert to similarity: similarity = 1 - distance.

Requirements:
  - pgvector extension must be enabled in Supabase (setup_supabase.sql)
  - candidates.embedding and jobs.embedding columns must be populated
"""

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def search_similar_candidates(
    db: Session,
    job_embedding: list[float],
    job_id: str,
    top_k: int = 50,
    min_similarity: float = 0.0,
) -> list[dict]:
    """
    Rank candidates for `job_id` by cosine similarity to `job_embedding`.

    Uses pgvector's `<=>` cosine distance operator directly in the DB so
    that only the top-K rows are returned — no in-memory sorting required.

    Candidates whose `embedding` is NULL (migrated from SQLite) are excluded.

    Args:
        db:             Active SQLAlchemy session.
        job_embedding:  384-dim list[float] from SBERT encode().
        job_id:         Filter to candidates who applied to this job.
        top_k:          Maximum results to return.
        min_similarity: Minimum cosine similarity threshold (0.0 – 1.0).

    Returns:
        List of dicts with keys: id, name, email, gyr_tier,
        probability_score, similarity.
    """
    # pgvector expects the vector as a string literal: '[0.1, 0.2, ...]'
    vec_str = "[" + ", ".join(f"{v:.8f}" for v in job_embedding) + "]"

    rows = db.execute(
        text("""
            SELECT
                id,
                name,
                email,
                gyr_tier,
                probability_score,
                ROUND(CAST(1 - (embedding <=> CAST(:vec AS vector)) AS NUMERIC), 6) AS similarity
            FROM candidates
            WHERE
                applied_job_id = :job_id
                AND embedding IS NOT NULL
                AND (1 - (embedding <=> CAST(:vec AS vector))) >= :min_sim
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
        """),
        {
            "vec":     vec_str,
            "job_id":  job_id,
            "min_sim": min_similarity,
            "top_k":   top_k,
        },
    )
    return [dict(row._mapping) for row in rows]


def get_job_embedding(db: Session, job_id: str) -> Optional[list[float]]:
    """
    Fetch the stored SBERT embedding for a job posting.
    Returns None if the job has no embedding yet.
    """
    row = db.execute(
        text("SELECT embedding FROM jobs WHERE id = :job_id"),
        {"job_id": job_id},
    ).fetchone()

    if row is None or row[0] is None:
        return None
    # pgvector returns the embedding as a list already
    return list(row[0])


def search_similar_jobs(
    db: Session,
    resume_embedding: list[float],
    top_k: int = 10,
    status_filter: str = "Active",
) -> list[dict]:
    """
    Find jobs most semantically similar to a resume embedding.
    Useful for recommending relevant job postings to an applicant.

    Args:
        db:               Active SQLAlchemy session.
        resume_embedding: 384-dim list[float] from SBERT encode().
        top_k:            Maximum results to return.
        status_filter:    Only include jobs with this status (default 'Active').

    Returns:
        List of dicts with keys: id, title, department, status, similarity.
    """
    vec_str = "[" + ", ".join(f"{v:.8f}" for v in resume_embedding) + "]"

    rows = db.execute(
        text("""
            SELECT
                id,
                title,
                department,
                status,
                ROUND(CAST(1 - (embedding <=> CAST(:vec AS vector)) AS NUMERIC), 6) AS similarity
            FROM jobs
            WHERE
                status = :status
                AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
        """),
        {
            "vec":    vec_str,
            "status": status_filter,
            "top_k":  top_k,
        },
    )
    return [dict(row._mapping) for row in rows]
