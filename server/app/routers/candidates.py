import mimetypes
import os
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from .. import models, schemas
from ..database import get_db
from ..services.file_service import extract_text_from_file, save_resume_bytes, UPLOADS_DIR
from ..services.ml_service import predict_resume_tier

router = APIRouter(
    prefix="/api",
    tags=["candidates"],
    redirect_slashes=False,
)

@router.post("/apply", response_model=schemas.Candidate)
async def apply_for_job(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    jobId: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Check if job exists
    job = db.query(models.JobPosting).filter(models.JobPosting.id == jobId).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Extract text from the resume
    try:
        resume_text = await extract_text_from_file(resume)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process resume file: {str(e)}")

    # Score resume via ML model — pass job description so the 770-feature
    # pipeline can compute both TF-IDF and SBERT cosine similarities.
    job_description = (job.description or "") + " " + (job.requirements or "")
    prob_score, gyr_tier = predict_resume_tier(resume_text, job_description)

    # Save candidate record first (without file path) to get the auto-generated ID
    db_candidate = models.Candidate(
        name=name,
        email=email,
        phone=phone,
        applied_job_id=jobId,
        probability_score=prob_score,
        gyr_tier=gyr_tier,
        status="Pending",
        resume_url=resume.filename,  # placeholder; updated below after we have the ID
        appliedDate=datetime.now().isoformat()
    )

    try:
        db.add(db_candidate)
        db.flush()  # assigns ID without committing, so we can use the ID for the filename

        # Persist the raw bytes to disk now that we have the candidate ID
        saved_bytes = getattr(resume, '_saved_bytes', None)
        if saved_bytes and resume.filename:
            rel_path = save_resume_bytes(str(db_candidate.id), resume.filename, saved_bytes)
            db_candidate.resume_url = rel_path

        # Recount from DB for concurrency safety instead of in-memory increment
        job.applicantsCount = (
            db.query(models.Candidate)
            .filter(models.Candidate.applied_job_id == jobId)
            .count()
        )
        db.commit()
        db.refresh(db_candidate)
        return db_candidate
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save application: {str(e)}")

@router.get("/candidates", response_model=List[schemas.Candidate])
def get_candidates(job_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Candidate)
    if job_id:
        query = query.filter(models.Candidate.applied_job_id == job_id)
    candidates = query.offset(skip).limit(limit).all()
    return candidates


@router.get("/candidates/{candidate_id}/resume")
def get_candidate_resume(candidate_id: str, db: Session = Depends(get_db)):
    """Streams the stored resume file (PDF or DOCX) for the given candidate."""
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not db_candidate.resume_url:
        raise HTTPException(status_code=404, detail="No resume file found for this candidate")

    # resume_url is stored as a relative path like 'uploads/<id>_<filename>'
    # Resolve against the uploads directory
    rel_path = db_candidate.resume_url  # e.g. 'uploads/abc123_resume.pdf'
    stored_filename = os.path.basename(rel_path)  # 'abc123_resume.pdf'
    file_path = UPLOADS_DIR / stored_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resume file not found on server")

    # Strip the '<candidate_id>_' prefix so the user sees the original filename
    original_filename = "_".join(stored_filename.split("_")[1:]) if "_" in stored_filename else stored_filename

    media_type, _ = mimetypes.guess_type(str(file_path))
    media_type = media_type or "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=original_filename,
        headers={"Content-Disposition": f'inline; filename="{original_filename}"'},
    )

@router.patch("/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate(candidate_id: str, candidate_update: schemas.CandidateUpdate, db: Session = Depends(get_db)):
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    update_data = candidate_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
        
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """Permanently deletes a single candidate record."""
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Update the parent job's applicantsCount before deleting
    if db_candidate.applied_job_id:
        job = db.query(models.JobPosting).filter(models.JobPosting.id == db_candidate.applied_job_id).first()
        if job and job.applicantsCount > 0:
            job.applicantsCount -= 1

    db.delete(db_candidate)
    db.commit()
    return {"message": f"Candidate {candidate_id} deleted successfully"}
