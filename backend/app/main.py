from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, health, profile, resumes, users
from app.core.config import get_settings

app = FastAPI(title="AI Job Copilot API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
