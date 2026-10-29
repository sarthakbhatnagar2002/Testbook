from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import COOKIE_NAME, decode_token


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = decode_token(token)
    if not user_id:
        return None
    return db.get(models.User, user_id)


def require_user(user: models.User | None = Depends(get_current_user)) -> models.User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user
