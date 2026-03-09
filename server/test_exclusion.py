import requests
import time
import sqlite3
import uuid
import datetime

BASE_URL = "http://127.0.0.1:8000/api"

def main():
    # 1. Create a Job
    job_data = {
        "title": "Exclusion Test Job",
        "department": "Engineering",
        "location": "Remote",
        "type": "Contract",
        "status": "Active",
        "postedDate": "2026-03-03T00:00:00.000Z",
        "description": "Test",
    }
    
    # We must start the server first before running this script
    try:
        job_res = requests.post(f"{BASE_URL}/jobs/", json=job_data)
        job_res.raise_for_status()
    except Exception as e:
        print("Failed to reach API or create job:", e)
        return

    job_id = job_res.json().get("id")
    print("Created Job:", job_id)

    # 2. Add candidates directly to DB to explicitly set their status 
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()

    cand1_id = str(uuid.uuid4())
    cand2_id = str(uuid.uuid4())

    # Add one Pending candidate
    cursor.execute(
        "INSERT INTO candidates (id, name, email, applied_job_id, probability_score, gyr_tier, status, appliedDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (cand1_id, "Pending Person", "pending@test.com", job_id, 50, "Red", "Pending", datetime.datetime.now().isoformat())
    )

    # Add one Shortlisted candidate
    cursor.execute(
        "INSERT INTO candidates (id, name, email, applied_job_id, probability_score, gyr_tier, status, appliedDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (cand2_id, "Shortlisted Person", "shortlisted@test.com", job_id, 95, "Green", "Shortlisted", datetime.datetime.now().isoformat())
    )
    conn.commit()
    print("Created Pending Candidate:", cand1_id)
    print("Created Shortlisted Candidate:", cand2_id)

    # 3. Delete the Job via API
    delete_res = requests.delete(f"{BASE_URL}/jobs/{job_id}")
    print("Delete Job Response:", delete_res.text)

    # 4. Read remaining candidates in DB
    cursor.execute("SELECT id, name, status, applied_job_id FROM candidates;")
    print("\nRemaining Candidates (Should keep only Shortlisted):")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
