"""Point d entree FastAPI - SUPMEAL API."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles as _StaticFiles
from starlette.websockets import WebSocket as _WebSocket
from starlette.websockets import WebSocketDisconnect as _WebSocketDisconnect

from app.api.v1.endpoints.cookbooks import (
    _ALLOWED_WS_ORIGINS,
    _extract_ws_token,
    _get_member_role_ws,
)
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.csrf import CSRFMiddleware
from app.core.ratelimit import general_limiter, import_limiter, upload_limiter
from app.core.ratelimit import message_limiter as _msg_limiter
from app.core.ratelimit import ws_limiter as _ws_limiter
from app.core.security import decode_access_token as _decode
from app.db.session import AsyncSessionLocal as _AsyncSessionLocal2
from app.db.session import engine
from app.models.cookbook import CookbookMessage
from app.models.user import User as _User2
from app.schemas.user import UserPublic as _UserPublic2
from app.services.connection_manager import manager as _manager

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


# ---------- Session (requis pour OAuth state Authlib) ----------
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=(settings.app_env == "production"),
)


# ---------- CSRF (double-submit cookie) ----------
app.add_middleware(CSRFMiddleware)


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


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Rate limit global + specifiques par chemin sensible."""
    if settings.app_env == "test":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method

    # Endpoints sensibles
    if path.startswith("/api/v1/import-export") and method == "POST" and not import_limiter.is_allowed(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Trop d imports. Reessayez plus tard."})
    if ("/image" in path or "/avatar" in path) and not upload_limiter.is_allowed(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Trop d uploads. Reessayez plus tard."})

    # General (toutes les routes /api/*)
    if path.startswith("/api/") and not general_limiter.is_allowed(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Trop de requetes. Reessayez plus tard."})

    return await call_next(request)


# ---------- CORS : liste blanche explicite (pas de wildcard) ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-CSRF-Token"],
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

# ---------- WebSocket (declare au niveau app pour eviter le bug FastAPI 0.115+ sur les WS routes) ----------
@app.websocket("/api/v1/cookbooks/{cookbook_id}/ws")
async def app_websocket_chat(websocket: _WebSocket, cookbook_id: str):
    await websocket.accept()
    origin = websocket.headers.get("origin")
    if origin and _ALLOWED_WS_ORIGINS and origin not in _ALLOWED_WS_ORIGINS:
        await websocket.close(code=4403)
        return
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4401)
        return
    payload = _decode(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return
    user_id = int(payload["sub"])
    if not _ws_limiter.is_allowed(str(user_id)):
        await websocket.close(code=4429)
        return
    try:
        cb_id = int(cookbook_id)
    except (TypeError, ValueError):
        await websocket.close(code=4400)
        return
    async with _AsyncSessionLocal2() as db:
        role = await _get_member_role_ws(db, cb_id, user_id)
        if role is None:
            await websocket.close(code=4403)
            return
    await _manager.connect(cb_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = (data.get("content") or "").strip()
            if not content:
                continue
            if not _msg_limiter.is_allowed(str(user_id)):
                continue
            async with _AsyncSessionLocal2() as db:
                msg = CookbookMessage(cookbook_id=cb_id, author_id=user_id, content=content[:2000])
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                author = await db.get(_User2, user_id)
            await _manager.broadcast(
                cb_id,
                {
                    "id": msg.id,
                    "author_id": user_id,
                    "author": _UserPublic2.model_validate(author).model_dump(),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                },
            )
    except _WebSocketDisconnect:
        _manager.disconnect(cb_id, websocket)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "env": settings.app_env, "version": app.version}


@app.get("/", tags=["root"])
async def root():
    return {"message": "SUPMEAL API", "docs": "/docs"}
