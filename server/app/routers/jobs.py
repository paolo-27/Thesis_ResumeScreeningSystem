from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    redirect_slashes=False,
)

@router.get("/", response_model=List[schemas.JobPosting])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(models.JobPosting).offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=schemas.JobPosting)
def read_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/{job_id}/stats")
def get_job_stats(job_id: str, db: Session = Depends(get_db)):
    """
    Returns real candidate counts broken down by GYR tier and status for a job.
    Replaces any Math.random() mock data in the frontend.
    """
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Count per gyr_tier in a single query
    tier_counts = (
        db.query(models.Candidate.gyr_tier, func.count(models.Candidate.id))
        .filter(models.Candidate.applied_job_id == job_id)
        .group_by(models.Candidate.gyr_tier)
        .all()
    )
    tier_map = {tier: count for tier, count in tier_counts}

    # Count per status
    status_counts = (
        db.query(models.Candidate.status, func.count(models.Candidate.id))
        .filter(models.Candidate.applied_job_id == job_id)
        .group_by(models.Candidate.status)
        .all()
    )
    status_map = {status: count for status, count in status_counts}

    total = sum(tier_map.values())

    return {
        "job_id": job_id,
        "total": total,
        "green": tier_map.get("Green", 0),
        "yellow": tier_map.get("Yellow", 0),
        "red": tier_map.get("Red", 0),
        "shortlisted": status_map.get("Shortlisted", 0),
        "rejected": status_map.get("Rejected", 0),
        "pending": status_map.get("Pending", 0),
    }

# Optional: Add endpoints to create/update jobs as needed by the admin panel
@router.post("/", response_model=schemas.JobPosting)
def create_job(job: schemas.JobPostingCreate, db: Session = Depends(get_db)):
    db_job = models.JobPosting(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete ALL candidates tied to this job, regardless of their status.
    # This includes Shortlisted candidates so that their probability_score
    # no longer contributes to the dashboard's average match score.
    deleted_count = (
        db.query(models.Candidate)
        .filter(models.Candidate.applied_job_id == job_id)
        .delete(synchronize_session="fetch")
    )

    db.delete(job)
    db.commit()
    return {
        "message": "Job and all associated candidates deleted successfully",
        "candidates_deleted": deleted_count,
    }

