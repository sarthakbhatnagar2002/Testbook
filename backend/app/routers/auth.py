from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..security import clear_session_cookie, hash_password, set_session_cookie, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut)
def register(body: schemas.RegisterIn, response: Response, db: Session = Depends(get_db)):
    existing = db.execute(select(models.User).where(models.User.email == body.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That email is already registered")

    user = models.User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(body: schemas.LoginIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    set_session_cookie(response, user.id)
    return user


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=schemas.UserOut | None)
def me(user: models.User | None = Depends(get_current_user)):
    return user
