from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user
from pydantic import BaseModel
from ..services.jd_parser import parse_job_description
from ..services.activity_logger import log_activity
from datetime import datetime

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    redirect_slashes=False,
)

@router.get("/", response_model=List[schemas.JobPosting])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = db.query(models.JobPosting).filter((models.JobPosting.is_deleted == False) | (models.JobPosting.is_deleted == None))
    if current_user.role == "HR":
        query = query.filter(models.JobPosting.created_by_id == current_user.id)
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/public", response_model=List[schemas.JobPosting])
def read_public_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Public endpoint for the applicant landing page to see all Active jobs."""
    jobs = db.query(models.JobPosting).filter(
        models.JobPosting.status == "Active",
        ((models.JobPosting.is_deleted == False) | (models.JobPosting.is_deleted == None))
    ).offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=schemas.JobPosting)
def read_job(job_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    job = db.query(models.JobPosting).filter(
        models.JobPosting.id == job_id,
        ((models.JobPosting.is_deleted == False) | (models.JobPosting.is_deleted == None))
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "HR" and job.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    return job

@router.get("/{job_id}/stats")
def get_job_stats(job_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """
    Returns real candidate counts broken down by GYR tier and status for a job.
    Replaces any Math.random() mock data in the frontend.
    """
    job = db.query(models.JobPosting).filter(
        models.JobPosting.id == job_id,
        ((models.JobPosting.is_deleted == False) | (models.JobPosting.is_deleted == None))
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "HR" and job.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view stats for this job")

    # Count per gyr_tier in a single query
    tier_counts = (
        db.query(models.Candidate.gyr_tier, func.count(models.Candidate.id))
        .filter(models.Candidate.applied_job_id == job_id)
        .filter((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
        .group_by(models.Candidate.gyr_tier)
        .all()
    )
    tier_map = {tier: count for tier, count in tier_counts}

    # Count per status
    status_counts = (
        db.query(models.Candidate.status, func.count(models.Candidate.id))
        .filter(models.Candidate.applied_job_id == job_id)
        .filter((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
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

class ParseRequest(BaseModel):
    description: str

@router.post("/parse")
def parse_jd(request: ParseRequest):
    return parse_job_description(request.description)

# Optional: Add endpoints to create/update jobs as needed by the admin panel
import json

@router.post("/", response_model=schemas.JobPosting)
def create_job(job: schemas.JobPostingCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_job_data = job.model_dump()
    db_job_data['created_by_id'] = current_user.id
    
    # Auto-extract structured fields from raw description if not provided
    if db_job_data.get('description'):
        parsed_data = parse_job_description(db_job_data['description'])
        if not db_job_data.get('salary') and parsed_data.get('salary'):
            db_job_data['salary'] = parsed_data['salary']
        if not db_job_data.get('parsedRequirements') and parsed_data.get('parsedRequirements'):
            db_job_data['parsedRequirements'] = json.dumps(parsed_data['parsedRequirements'])
        if parsed_data.get('cleanedDescription'):
            db_job_data['description'] = parsed_data['cleanedDescription']
            
    db_job = models.JobPosting(**db_job_data)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    background_tasks.add_task(log_activity, "JOB_CREATED", f"New job posting created: {db_job.title}", current_user.id)
    
    return db_job

@router.delete("/{job_id}")
def delete_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    job = db.query(models.JobPosting).filter(
        models.JobPosting.id == job_id,
        ((models.JobPosting.is_deleted == False) | (models.JobPosting.is_deleted == None))
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "HR" and job.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    # Delete ALL candidates tied to this job, regardless of their status.
    # This includes Shortlisted candidates so that their probability_score
    # no longer contributes to the dashboard's average match score.
    deleted_count = (
        db.query(models.Candidate)
        .filter(models.Candidate.applied_job_id == job_id)
        .filter((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
        .update({
            "is_deleted": True,
            "deleted_at": datetime.now().isoformat(),
            "deleted_by_id": current_user.id
        }, synchronize_session=False)
    )

    job.is_deleted = True
    job.deleted_at = datetime.now().isoformat()
    job.deleted_by_id = current_user.id
    db.commit()
    
    background_tasks.add_task(log_activity, "JOB_DELETED", f"Job posting deleted: {job.title}", current_user.id)
    
    return {
        "message": "Job and all associated candidates deleted successfully",
        "candidates_deleted": deleted_count,
    }

