from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import auth, practice, profile, questions, subjects, uploads

settings = get_settings()

app = FastAPI(title="MCQ Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(questions.router)
app.include_router(practice.router)
app.include_router(profile.router)
# Registered before the static mount below: an exact-path POST route is tried
# before Starlette falls through to the path-prefix Mount.
app.include_router(uploads.router)

upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads_static")


@app.get("/health")
def health():
    return {"ok": True}
