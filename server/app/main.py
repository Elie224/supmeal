"""Point d entree FastAPI - SUPMEAL API."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles as _StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
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


# ---------- Middleware headers de securite ----------

_DEV_DOCS_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


def _build_csp(request_origin):
    """Construit la politique CSP. Swagger UI necessite quelques assouplissements."""
    directives = [
        "default-src ''self''",
        "img-src ''self'' data: blob:",
        "connect-src ''self'' ws: wss:",
        "font-src ''self'' data:",
        "frame-ancestors ''none''",
        "base-uri ''self''",
        "form-action ''self''",
        "object-src ''none''",
    ]
    if request_origin in _DEV_DOCS_ORIGINS or request_origin in settings.cors_origins_list:
        directives.insert(1, "script-src ''self'' ''unsafe-inline'' ''unsafe-eval''")
        directives.insert(2, "style-src ''self'' ''unsafe-inline''")
    else:
        directives.insert(1, "script-src ''self''")
        directives.insert(2, "style-src ''self''")
    return "; ".join(directives)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = _build_csp(request.headers.get("origin"))
    return response


from app.core.ratelimit import general_limiter, import_limiter, upload_limiter


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Rate limit global + specifiques par chemin sensible."""
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method

    # Endpoints sensibles
    if path.startswith("/api/v1/import-export") and method == "POST":
        if not import_limiter.is_allowed(client_ip):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Trop d imports. Reessayez plus tard."})
    if "/image" in path or "/avatar" in path:
        if not upload_limiter.is_allowed(client_ip):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Trop d uploads. Reessayez plus tard."})

    # General (toutes les routes /api/*)
    if path.startswith("/api/"):
        if not general_limiter.is_allowed(client_ip):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Trop de requetes. Reessayez plus tard."})

    return await call_next(request)


# ---------- CORS : liste blanche explicite (pas de wildcard) ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# ---------- Fichiers statiques avec cache + headers de securite ----------

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


class CachedStaticFiles(_StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=604800"
            response.headers["Content-Security-Policy"] = "default-src ''none''; img-src ''self''"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response


app.mount("/uploads", CachedStaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "env": settings.app_env, "version": app.version}


@app.get("/", tags=["root"])
async def root():
    return {"message": "SUPMEAL API", "docs": "/docs"}
