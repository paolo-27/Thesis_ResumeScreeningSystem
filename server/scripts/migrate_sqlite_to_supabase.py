"""
migrate_sqlite_to_supabase.py
──────────────────────────────────────────────────────────────────────────────
One-shot migration script: copies all data from the local SQLite file into
the Supabase PostgreSQL database.

Usage (from the `server/` directory):
    python scripts/migrate_sqlite_to_supabase.py

Requirements:
  - server/.env must contain a valid DATABASE_URL (PostgreSQL / Supabase)
  - The PostgreSQL tables must already exist (run create_tables.sql first)
  - The local SQLite file path is auto-detected (db.sqlite3 or app/resume_screening.db)

The migration is IDEMPOTENT — rows that already exist (same primary key) are
skipped via ON CONFLICT DO NOTHING. It is safe to re-run.

Embedding columns are left NULL for migrated rows; they will be backfilled
lazily the next time a candidate is re-screened.
"""

import os
import sys
import sqlite3

# ── Resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SERVER_DIR)

# Load .env before importing anything that reads os.environ
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(SERVER_DIR, ".env"))

# ── SQLite source ─────────────────────────────────────────────────────────────
SQLITE_CANDIDATES = [
    os.path.join(SERVER_DIR, "db.sqlite3"),
    os.path.join(SERVER_DIR, "app", "resume_screening.db"),
    os.path.join(SERVER_DIR, "database.db"),
]

def find_sqlite() -> str | None:
    for path in SQLITE_CANDIDATES:
        if os.path.exists(path):
            return path
    return None

# ── PostgreSQL target ─────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text

PG_URL = os.getenv("DATABASE_URL")
if not PG_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

pg_engine = create_engine(PG_URL, pool_pre_ping=True)


def migrate():
    sqlite_path = find_sqlite()
    if not sqlite_path:
        print("No SQLite file found. Nothing to migrate.")
        return

    print(f"Source SQLite: {sqlite_path}")
    print(f"Target PG:     {PG_URL.split('@')[1] if '@' in PG_URL else PG_URL}")
    print()

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    with pg_engine.connect() as pg:
        # ── Users ──────────────────────────────────────────────────────────
        users = src.execute("SELECT * FROM users").fetchall()
        print(f"Migrating {len(users)} users …")
        for row in users:
            pg.execute(
                text("""
                    INSERT INTO users
                        (id, employee_number, password_hash, name, email,
                         phone, company, location, avatar_color, role,
                         is_active, force_reset, created_at)
                    VALUES
                        (:id, :employee_number, :password_hash, :name, :email,
                         :phone, :company, :location, :avatar_color, :role,
                         :is_active, :force_reset, :created_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                dict(row),
            )
        pg.commit()
        print(f"  ✓ {len(users)} users done.\n")

        # ── Jobs ───────────────────────────────────────────────────────────
        jobs = src.execute("SELECT * FROM jobs").fetchall()
        print(f"Migrating {len(jobs)} jobs …")
        for row in jobs:
            d = dict(row)
            pg.execute(
                text("""
                    INSERT INTO jobs
                        (id, title, department, location, type, status,
                         "applicantsCount", "postedDate", description,
                         requirements, salary, "parsedRequirements", created_by_id)
                    VALUES
                        (:id, :title, :department, :location, :type, :status,
                         :applicantsCount, :postedDate, :description,
                         :requirements, :salary, :parsedRequirements, :created_by_id)
                    ON CONFLICT (id) DO NOTHING
                """),
                d,
            )
        pg.commit()
        print(f"  ✓ {len(jobs)} jobs done.\n")

        # ── Candidates ─────────────────────────────────────────────────────
        candidates = src.execute("SELECT * FROM candidates").fetchall()
        print(f"Migrating {len(candidates)} candidates …")
        for row in candidates:
            d = dict(row)
            pg.execute(
                text("""
                    INSERT INTO candidates
                        (id, name, email, phone, applied_job_id,
                         probability_score, gyr_tier, status,
                         resume_url, "appliedDate")
                    VALUES
                        (:id, :name, :email, :phone, :applied_job_id,
                         :probability_score, :gyr_tier, :status,
                         :resume_url, :appliedDate)
                    ON CONFLICT (id) DO NOTHING
                """),
                d,
            )
        pg.commit()
        print(f"  ✓ {len(candidates)} candidates done.\n")

        # ── Activity Logs ──────────────────────────────────────────────────
        try:
            logs = src.execute("SELECT * FROM activity_logs").fetchall()
            print(f"Migrating {len(logs)} activity logs …")
            for row in logs:
                pg.execute(
                    text("""
                        INSERT INTO activity_logs
                            (id, user_id, action_type, description, timestamp)
                        VALUES
                            (:id, :user_id, :action_type, :description, :timestamp)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    dict(row),
                )
            pg.commit()
            print(f"  ✓ {len(logs)} activity logs done.\n")
        except Exception as e:
            print(f"  ⚠ Activity logs skipped: {e}\n")

    src.close()
    print("Migration complete!")
    print()
    print("Note: 'embedding' columns are NULL for migrated rows.")
    print("They will be populated automatically on the next screening run.")


if __name__ == "__main__":
    migrate()
