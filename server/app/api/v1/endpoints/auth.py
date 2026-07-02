"""Endpoints d'authentification locale."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.core.config import get_settings as _auth_settings
from app.core.ratelimit import login_limiter, register_limiter
from fastapi import Request
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import AuthProvider, User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not register_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Reessayez plus tard.")
    # Defense : complexite minimale du mot de passe (defense en profondeur, le schema impose >=8)
    pwd = payload.password
    if (not any(c.islower() for c in pwd) or not any(c.isupper() for c in pwd) or not any(c.isdigit() for c in pwd)):
        raise HTTPException(
            status_code=422,
            detail="Le mot de passe doit contenir au moins une minuscule, une majuscule et un chiffre.",
        )
    # Verifier unicite email et username
    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou nom d'utilisateur deja utilise",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.LOCAL,
        is_verified=False,
        dietary_preferences=payload.dietary_preferences,
        allergies=payload.allergies,
        favorite_cuisines=payload.favorite_cuisines,
        default_servings=payload.default_servings,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Reessayez plus tard.")
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte desactive")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/exchange", response_model=TokenResponse)
async def exchange_oauth_code(payload: dict, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Echange un code OAuth a usage unique (1 min) contre un JWT.
    Le navigateur appelle /auth/callback?code=XXX puis POST /auth/exchange{code}.
    Cela evite d avoir le token dans l URL (logs, referrer, historique)."""
    from app.api.v1.endpoints._oauth_codes import consume_code
    from app.schemas.user import UserRead as _UserRead
    from app.core.security import decode_access_token
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
    return TokenResponse(access_token=token, user=_UserRead.model_validate(user))

