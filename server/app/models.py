from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
import uuid
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class JobPosting(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    department = Column(String, nullable=False)
    location = Column(String, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default="Active")  # 'Active' | 'Draft' | 'Closed'
    applicantsCount = Column(Integer, default=0)
    postedDate = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)  # Store as a JSON string

    candidates = relationship("Candidate", back_populates="job")

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    applied_job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    probability_score = Column(Float, nullable=False)
    gyr_tier = Column(String, nullable=False)  # 'Green' | 'Yellow' | 'Red'
    status = Column(String, default="Pending")  # 'Pending' | 'Shortlisted' | 'Rejected'
    resume_url = Column(String, nullable=True)
    appliedDate = Column(String, nullable=False)

    job = relationship("JobPosting", back_populates="candidates")
