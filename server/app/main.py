"""
main.py — FastAPI application entry point for the Veridian RSS.

IMPORTANT: Tables are no longer auto-created here via Base.metadata.create_all().
For PostgreSQL / Supabase, tables must be created via the provided SQL scripts:
  1. server/scripts/setup_supabase.sql   — enables pgvector extension
  2. server/scripts/create_tables.sql    — creates all 4 tables + indexes

Run those scripts ONCE in the Supabase SQL Editor before first launch.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import jobs, candidates, logs, auth_router

app = FastAPI(title="GYR Resume Screening API")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:3000",
        "https://thesis-resume-screening-system.vercel.app" # Add your Vercel URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(logs.router)
app.include_router(auth_router.router)


@app.get("/")
def read_root():
    return {"message": "GYR Resume Screening API is running"}
