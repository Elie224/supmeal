"""Endpoints d'authentification locale."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings as _auth_settings
from app.core.deps import CurrentUser, get_db
from app.core.pwned import is_pwned
from app.core.ratelimit import login_limiter, register_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import AuthProvider, User
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    settings = _auth_settings()
    if settings.app_env != "test" and not register_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Reessayez plus tard.")
    # Defense : complexite minimale du mot de passe (defense en profondeur, le schema impose >=8)
    pwd = payload.password
    if (not any(c.islower() for c in pwd) or not any(c.isupper() for c in pwd) or not any(c.isdigit() for c in pwd)):
        raise HTTPException(
            status_code=422,
            detail="Le mot de passe doit contenir au moins une minuscule, une majuscule et un chiffre.",
        )
    # Verifier qu il n apparait pas dans des fuites connues (HIBP k-anonymity)
    if settings.app_env != "test" and is_pwned(pwd):
        raise HTTPException(
            status_code=422,
            detail="Ce mot de passe est apparu dans des fuites de donnees publiques. Veuillez en choisir un autre.",
        )
    # Verifier unicite email et username
    by_email = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    email_user = by_email.scalar_one_or_none()

    by_username = await db.execute(select(User).where(User.username == payload.username))
    username_user = by_username.scalar_one_or_none()

    # Cas de reprise: un compte local non verifie existe deja pour cet email.
    # On met a jour ce compte au lieu de bloquer l'inscription.
    can_reactivate = (
        email_user is not None
        and email_user.auth_provider == AuthProvider.LOCAL
        and not email_user.is_verified
        and (username_user is None or username_user.id == email_user.id)
    )
    if can_reactivate:
        email_user.username = payload.username
        email_user.full_name = payload.full_name
        email_user.hashed_password = hash_password(payload.password)
        email_user.is_active = True
        email_user.is_verified = True
        email_user.dietary_preferences = payload.dietary_preferences
        email_user.allergies = payload.allergies
        email_user.favorite_cuisines = payload.favorite_cuisines
        email_user.default_servings = payload.default_servings
        await db.commit()
        await db.refresh(email_user)

        token = create_access_token(email_user.id)
        body = TokenResponse(access_token=token, user=UserRead.model_validate(email_user)).model_dump(mode="json")
        from fastapi.responses import JSONResponse
        resp = JSONResponse(content=body, status_code=status.HTTP_201_CREATED)
        _set_auth_cookies(resp, token, settings)
        return resp

    if email_user or username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou nom d'utilisateur deja utilise",
        )

    user = User(
        email=normalized_email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.LOCAL,
        is_verified=True,
        dietary_preferences=payload.dietary_preferences,
        allergies=payload.allergies,
        favorite_cuisines=payload.favorite_cuisines,
        default_servings=payload.default_servings,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    settings = _auth_settings()
    body = TokenResponse(access_token=token, user=UserRead.model_validate(user)).model_dump(mode="json")
    from fastapi.responses import JSONResponse
    resp = JSONResponse(content=body, status_code=status.HTTP_201_CREATED)
    _set_auth_cookies(resp, token, settings)
    return resp


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    settings = _auth_settings()
    if settings.app_env != "test" and not login_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Reessayez plus tard.")
    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte desactive")

    token = create_access_token(user.id)
    settings = _auth_settings()
    body = TokenResponse(access_token=token, user=UserRead.model_validate(user)).model_dump(mode="json")
    from fastapi.responses import JSONResponse
    resp = JSONResponse(content=body)
    _set_auth_cookies(resp, token, settings)
    return resp


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/exchange", response_model=TokenResponse)
async def exchange_oauth_code(payload: dict, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Echange un code OAuth a usage unique (1 min) contre un JWT.
    Le navigateur appelle /auth/callback?code=XXX puis POST /auth/exchange{code}.
    Cela evite d avoir le token dans l URL (logs, referrer, historique)."""
    from app.api.v1.endpoints._oauth_codes import consume_code
    from app.core.security import decode_access_token
    from app.schemas.user import UserRead as _UserRead
    code = (payload or {}).get("code", "")
    if not code or not isinstance(code, str) or len(code) > 128:
        raise HTTPException(status_code=400, detail="Code invalide")
    token = consume_code(code)
    if not token:
        raise HTTPException(status_code=400, detail="Code expire ou invalide")
    decoded = decode_access_token(token)
    if not decoded or "sub" not in decoded:
        raise HTTPException(status_code=400, detail="Token invalide")
    from sqlalchemy import select as _select
    result = await db.execute(_select(User).where(User.id == int(decoded["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur invalide")
    settings = _auth_settings()
    body = TokenResponse(access_token=token, user=_UserRead.model_validate(user)).model_dump(mode="json")
    from fastapi.responses import JSONResponse
    resp = JSONResponse(content=body)
    _set_auth_cookies(resp, token, settings)
    return resp


def _set_auth_cookies(response: Response, token: str, settings) -> None:
    """Pose le JWT en cookie httpOnly + un token CSRF (double-submit pattern)."""
    is_prod = settings.app_env == "production"
    # Le token : httpOnly, secure en prod, SameSite=Lax (suffit pour une SPA, pas de cross-site form post)
    response.set_cookie(
        key="supmeal_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    # Le CSRF : lisible par le JS (pour qu il puisse l envoyer en header X-CSRF-Token)
    response.set_cookie(
        key="supmeal_csrf",
        value=secrets.token_urlsafe(32),
        httponly=False,
        secure=is_prod,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("supmeal_token", path="/")
    response.delete_cookie("supmeal_csrf", path="/")


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    """Supprime les cookies d authentification."""
    _clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.get("/csrf")
async def csrf_token(response: Response) -> dict:
    """Renvoie un token CSRF (double-submit cookie pattern).
    Le serveur pose un cookie lisible par le JS, le front l envoie en header X-CSRF-Token."""
    settings = _auth_settings()
    is_prod = settings.app_env == "production"
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="supmeal_csrf",
        value=token,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return {"csrf_token": token}

