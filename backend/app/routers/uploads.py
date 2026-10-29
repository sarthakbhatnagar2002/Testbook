import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from .. import models
from ..config import get_settings
from ..deps import require_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, _user: models.User = Depends(require_user)):
    ext = ALLOWED_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PNG, JPEG, WebP or GIF images are allowed")

    body = await file.read()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image must be 5MB or smaller")
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}{ext}"
    (upload_dir / name).write_bytes(body)

    return {"url": f"/uploads/{name}"}
