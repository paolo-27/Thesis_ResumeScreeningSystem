import io
import mimetypes
import os
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, Response
import requests
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List, Optional
from datetime import datetime
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user
from ..services.file_service import extract_text_from_file, save_resume_bytes
from ..services.ml_service import predict_resume_tier, predict_resume_tier_with_embedding, get_candidate_insights
from ..services.activity_logger import log_activity
from ..services.email_service import send_applicant_status_email

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
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    # Check if job exists
    job = db.query(models.JobPosting).filter(models.JobPosting.id == jobId).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Extract text from the resume (async — properly awaits the network read)
    try:
        resume_text = await extract_text_from_file(resume)
    except Exception as e:
        background_tasks.add_task(send_applicant_status_email, email=email, name=name, status="error", job_title=job.title, details=f"Formatting issue: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process resume file: {str(e)}")

    # Score resume via ML model AND capture the SBERT embedding for pgvector storage.
    # CPU-bound work is offloaded to a thread-pool worker to avoid blocking the event loop.
    job_description = (job.description or "") + " " + (job.requirements or "")
    try:
        prob_score, gyr_tier, resume_embedding = await run_in_threadpool(
            predict_resume_tier_with_embedding, resume_text, job_description
        )
    except Exception as e:
        background_tasks.add_task(send_applicant_status_email, email=email, name=name, status="error", job_title=job.title, details=f"We encountered an issue during the screening process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to screen resume: {str(e)}")

    # Snapshot the resume bytes and original filename before entering the
    # threadpool (UploadFile internals must not be accessed from another thread).
    saved_bytes = getattr(resume, '_saved_bytes', None)
    original_filename = resume.filename
    job_title = job.title  # capture before threadpool to avoid lazy-load issues
    job_owner_id = job.created_by_id

    # All remaining work (DB flush/commit + sync disk write) is blocking I/O
    # that must also be offloaded to the thread-pool.
    def _save_candidate() -> models.Candidate:
        db_candidate = models.Candidate(
            name=name,
            email=email,
            phone=phone,
            applied_job_id=jobId,
            probability_score=prob_score,
            gyr_tier=gyr_tier,
            status="Pending",
            resume_url=original_filename,  # placeholder; updated below after we have the ID
            appliedDate=datetime.now().isoformat()
        )

        try:
            db.add(db_candidate)
            db.flush()  # assigns ID without committing, so we can use it for the filename

            # Persist the raw bytes to disk now that we have the candidate ID
            if saved_bytes and original_filename:
                rel_path = save_resume_bytes(str(db_candidate.id), original_filename, saved_bytes)
                db_candidate.resume_url = rel_path

            # Store the SBERT embedding for pgvector similarity search.
            # resume_embedding is a plain list[float]; SQLAlchemy + pgvector
            # handles the conversion to the vector column type.
            if resume_embedding:
                db_candidate.embedding = resume_embedding

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
            raise e

    try:
        db_candidate = await run_in_threadpool(_save_candidate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save application: {str(e)}")

    # Log the activity asynchronously via BackgroundTask under the job owner
    background_tasks.add_task(log_activity, "RESUME_UPLOADED", f"New resume uploaded: {name} applied for {job_title}", job_owner_id)

    # Send success email via BackgroundTask
    match_percentage = int(prob_score * 100) if prob_score is not None else 0
    background_tasks.add_task(send_applicant_status_email, email=email, name=name, status="success", job_title=job_title, match_percentage=match_percentage)

    return db_candidate

@router.get("/candidates", response_model=List[schemas.Candidate])
def get_candidates(job_id: Optional[str] = None, skip: int = 0, limit: int = 10000, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = db.query(models.Candidate).filter((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
    if current_user.role == "HR":
        query = query.join(models.JobPosting).filter(models.JobPosting.created_by_id == current_user.id)
    if job_id:
        query = query.filter(models.Candidate.applied_job_id == job_id)
    candidates = query.offset(skip).limit(limit).all()
    return candidates


@router.get("/candidates/{candidate_id}/resume")
def get_candidate_resume(candidate_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Streams the stored resume file (PDF or DOCX) for the given candidate."""
    db_candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        ((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
    ).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == "HR" and (not db_candidate.job or db_candidate.job.created_by_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this candidate")
    if not db_candidate.resume_url:
        raise HTTPException(status_code=404, detail="No resume file found for this candidate")

    # Resolve against Supabase Storage
    stored_path = db_candidate.resume_url
    if stored_path.startswith("uploads/"):
        raise HTTPException(status_code=404, detail="Legacy resume file not found on server")

    url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/resumes/{stored_path}"
    headers = {
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
        "apikey": os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Resume file not found in storage")

    stored_filename = os.path.basename(stored_path)
    original_filename = stored_filename

    media_type, _ = mimetypes.guess_type(stored_filename)
    media_type = media_type or "application/octet-stream"

    return Response(
        content=response.content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{original_filename}"'},
    )


@router.get("/candidates/{candidate_id}/insights")
def get_insights(candidate_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Computes and returns SHAP feature importance + raw similarity scores for a candidate."""
    import PyPDF2
    from docx import Document as DocxDocument

    db_candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        ((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
    ).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == "HR" and (not db_candidate.job or db_candidate.job.created_by_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view insights for this candidate")
    if not db_candidate.resume_url:
        raise HTTPException(status_code=404, detail="No resume file found for this candidate")

    # Resolve file path from Supabase Storage
    stored_path = db_candidate.resume_url
    if stored_path.startswith("uploads/"):
        raise HTTPException(status_code=404, detail="Legacy resume file not found on server")

    url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/resumes/{stored_path}"
    headers = {
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
        "apikey": os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Resume file not found in storage")

    # Extract resume text directly from disk (no UploadFile needed)
    resume_bytes = response.content
    resume_text = ""
    stored_filename = os.path.basename(stored_path)
    fname = stored_filename.lower()
    
    if fname.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(resume_bytes))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                resume_text += t + "\n"
    elif fname.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(resume_bytes))
        for para in doc.paragraphs:
            if para.text:
                resume_text += para.text + "\n"
    else:
        try:
            resume_text = resume_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass
    resume_text = resume_text.strip()

    # Fetch job description from DB
    job_description = ""
    if db_candidate.applied_job_id:
        job = db.query(models.JobPosting).filter(
            models.JobPosting.id == db_candidate.applied_job_id
        ).first()
        if job:
            job_description = ((job.description or "") + " " + (job.requirements or "")).strip()

    try:
        result = get_candidate_insights(resume_text, job_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights computation failed: {str(e)}")

    return result

@router.patch("/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate(candidate_id: str, candidate_update: schemas.CandidateUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        ((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
    ).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == "HR" and (not db_candidate.job or db_candidate.job.created_by_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this candidate")
    
    update_data = candidate_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
        
    db.commit()
    db.refresh(db_candidate)
    
    if candidate_update.status:
        job_title = db_candidate.job.title if db_candidate.job else "a job"
        background_tasks.add_task(log_activity, "STATUS_UPDATED", f"{db_candidate.name}'s status was updated to {candidate_update.status} for {job_title}", current_user.id)
        
    return db_candidate

@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Soft deletes a single candidate record."""
    db_candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        ((models.Candidate.is_deleted == False) | (models.Candidate.is_deleted == None))
    ).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if current_user.role == "HR" and (not db_candidate.job or db_candidate.job.created_by_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this candidate")

    # Update the parent job's applicantsCount before deleting
    if db_candidate.applied_job_id:
        job = db.query(models.JobPosting).filter(models.JobPosting.id == db_candidate.applied_job_id).first()
        if job and job.applicantsCount > 0:
            job.applicantsCount -= 1

    db_candidate.is_deleted = True
    db_candidate.deleted_at = datetime.now().isoformat()
    db_candidate.deleted_by_id = current_user.id
    db.commit()
    return {"message": f"Candidate {candidate_id} deleted successfully"}
