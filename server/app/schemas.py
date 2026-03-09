from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class JobPostingBase(BaseModel):
    title: str
    department: str
    location: str
    type: str
    status: str = "Active"
    applicantsCount: int = 0
    postedDate: str
    description: Optional[str] = None
    requirements: Optional[str] = None

class JobPostingCreate(JobPostingBase):
    pass

class JobPosting(JobPostingBase):
    id: str
    model_config = ConfigDict(from_attributes=True)

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    applied_job_id: Optional[str] = None  # nullable — orphaned when a job is deleted
    probability_score: float
    gyr_tier: str
    status: str = "Pending"
    resume_url: Optional[str] = None
    appliedDate: str

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    status: Optional[str] = None

class Candidate(CandidateBase):
    id: str
    model_config = ConfigDict(from_attributes=True)
