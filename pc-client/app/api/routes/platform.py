from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.platform_uploader import upload_pending_records


router = APIRouter()


@router.post("/upload")
def trigger_upload(db: Session = Depends(get_db)) -> dict:
    result = upload_pending_records(db)
    return result
