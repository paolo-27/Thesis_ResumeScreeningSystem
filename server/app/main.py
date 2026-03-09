from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import jobs, candidates

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GYR Resume Screening API")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(candidates.router)

@app.get("/")
def read_root():
    return {"message": "GYR Resume Screening API is running"}
