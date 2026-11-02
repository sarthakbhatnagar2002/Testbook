from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import auth, chapters, practice, profile, subjects

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
app.include_router(chapters.router)
app.include_router(practice.router)
app.include_router(profile.router)

# Questions carry no uploaded images anymore (content is fixed, pre-seeded
# text MCQs) -- this mount only serves any images uploaded by the earlier
# user-generated-content era, kept so old links don't 404.
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads_static")


@app.get("/health")
def health():
    return {"ok": True}
