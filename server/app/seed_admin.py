"""
Seed script: creates the initial Admin user in the database.
Run once after first launch:  python -m app.seed_admin

Default credentials:
  Employee Number : ADMIN-001
  Password        : admin123

Change the password immediately after first login!
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app import models
from app.auth import get_password_hash

def seed():
    # Create all tables (User, etc.) if they don't exist yet
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Only seed if no Admin exists
        existing = db.query(models.User).filter(models.User.role == "Admin").first()
        if existing:
            print(f"Admin already exists: {existing.employee_number}")
            return

        admin = models.User(
            employee_number="ADMIN-001",
            password_hash=get_password_hash("admin123"),
            name="System Administrator",
            email="admin@veridian.local",
            company="Veridian HR",
            role="Admin",
            is_active=1,
            force_reset=1,  # Force password change on first login
        )
        db.add(admin)
        db.commit()
        print("   Admin user created!")
        print("   Employee Number : ADMIN-001")
        print("   Password        : admin123  ← change this on first login!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
