from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from .config import get_settings

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"uid": user_id, "iat": now, "exp": now + timedelta(seconds=MAX_AGE_SECONDS)}
    return jwt.encode(payload, settings.session_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=[ALGORITHM])
        return payload.get("uid")
    except jwt.PyJWTError:
        return None


def set_session_cookie(response: Response, user_id: str) -> None:
    settings = get_settings()
    # SameSite=None is required once the frontend and backend live on
    # different origins (e.g. two separate Render services) — browsers then
    # also require Secure on the cookie, which HTTPS-only Render satisfies.
    samesite = settings.cookie_samesite
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_token(user_id),
        httponly=True,
        samesite=samesite,
        secure=settings.is_production or samesite == "none",
        path="/",
        max_age=MAX_AGE_SECONDS,
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    samesite = settings.cookie_samesite
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite=samesite,
        secure=settings.is_production or samesite == "none",
    )
