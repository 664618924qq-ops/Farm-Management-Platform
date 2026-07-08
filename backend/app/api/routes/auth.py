from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import LoginPayload

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> dict:
    user = (
        db.query(User)
        .filter(User.username == payload.username, User.password == payload.password)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "token": f"demo-token-{user.username}",
        "user": {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name,
            "role": user.role,
        },
    }
