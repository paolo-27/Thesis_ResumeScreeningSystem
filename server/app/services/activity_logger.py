from sqlalchemy.orm import Session
from ..models import ActivityLog
from ..database import SessionLocal
import datetime
import traceback

def log_activity(action_type: str, description: str, user_id: str = None):
    """
    Background task to securely log a system activity.
    Uses its own database session to avoid DetachedInstanceError.
    """
    db = SessionLocal()
    try:
        new_log = ActivityLog(
            user_id=user_id,
            action_type=action_type,
            description=description,
            timestamp=datetime.datetime.utcnow().isoformat()
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log activity: {e}")
        traceback.print_exc()
    finally:
        db.close()
