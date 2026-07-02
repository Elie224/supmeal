"""Point d'entree FastAPI - SUPMEAL API."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialisation : s'assurer que le dossier d'uploads existe
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup
    await engine.dispose()


app = FastAPI(
    title="SUPMEAL API",
    description="API REST pour la gestion de recettes et planification de repas.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS : liste blanche explicite (pas de wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# Fichiers statiques pour les images uploadees
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
# Fichiers statiques avec cache 7j
from starlette.responses import Response
from starlette.staticfiles import StaticFiles as _StaticFiles
class CachedStaticFiles(_StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=604800"
        return response
app.mount("/uploads", CachedStaticFiles(directory=settings.upload_dir), name="uploads")

# Routes API
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env, "version": app.version}


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "SUPMEAL API", "docs": "/docs"}