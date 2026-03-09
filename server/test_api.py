from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base
import io

client = TestClient(app)

# Recreate the DB tables before testing
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "GYR Resume Screening API is running"}

def test_create_and_read_job():
    # Insert a job posting specifically for our resume schema
    job_data = {
        "title": "Software Engineer",
        "department": "Engineering",
        "location": "Remote",
        "type": "Full-Time",
        "status": "Active",
        "postedDate": "2026-03-03T00:00:00Z"
    }
    # Notice this goes directly to our router's POST which we created
    response = client.post("/api/jobs/", json=job_data)
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]

    # Test GET jobs
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_apply_for_job():
    # First get the job we just created
    response = client.get("/api/jobs/")
    job_id = response.json()[0]["id"]

    # Submit candidate form
    test_resume = b"Software Engineer with 5 years of Python experience." # Fake Text Resume
    files = {
        "resume": ("test.txt", test_resume, "text/plain")
    }
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "jobId": job_id
    }
    
    response = client.post("/api/apply", data=data, files=files)
    assert response.status_code == 200, response.text
    response_json = response.json()
    assert response_json["name"] == "John Doe"
    assert response_json["status"] == "Pending"
    # Should be Green, Yellow or Red
    assert response_json["gyr_tier"] in ["Green", "Yellow", "Red"]

def test_get_candidates():
    response = client.get("/api/candidates")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["name"] == "John Doe"

if __name__ == "__main__":
    print("Testing Root API Endpoint...")
    test_read_main()
    print("Testing Job Creation & Retrieval...")
    test_create_and_read_job()
    print("Testing Job Application with Fake PDF...")
    test_apply_for_job()
    print("Testing Candidate Retrieval...")
    test_get_candidates()
    print("All tests passed successfully!")
