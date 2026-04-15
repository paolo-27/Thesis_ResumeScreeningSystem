from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"],
    redirect_slashes=False,
)

@router.get("/recent", response_model=List[schemas.ActivityLog])
def get_recent_logs(limit: int = 15, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Fetch the most recent activity logs."""
    try:
        query = db.query(models.ActivityLog)
        if current_user.role == "HR":
            query = query.filter(models.ActivityLog.user_id == current_user.id)
        logs = query.order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

@router.delete("/clear")
def clear_all_logs(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Delete activity logs from the database."""
    try:
        if current_user.role == "HR":
            deleted_count = db.query(models.ActivityLog).filter(models.ActivityLog.user_id == current_user.id).delete()
        else:
            deleted_count = db.query(models.ActivityLog).delete()
        db.commit()
        return {"message": "All activity logs cleared successfully", "deleted_count": deleted_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")
