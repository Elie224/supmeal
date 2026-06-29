"""OAuth2 : Google, GitHub, Microsoft."""

from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.config import Config

from app.core.config import get_settings
from app.core.deps import get_db
from app.core.security import create_access_token
from app.models.user import AuthProvider, User
from app.schemas.user import UserPublic

router = APIRouter()
settings = get_settings()

# Config authlib : on lit directement depuis settings (pas de mapping .env)
config = Config()

oauth = OAuth(config)

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )

if settings.github_client_id and settings.github_client_secret:
    oauth.register(
        name="github",
        api_base_url="https://api.github.com/",
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        client_kwargs={"scope": "user:email"},
    )

if settings.microsoft_client_id and settings.microsoft_client_secret:
    oauth.register(
        name="microsoft",
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_id=settings.microsoft_client_id,
        client_secret=settings.microsoft_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )


def _is_provider_configured(provider: str) -> bool:
    return getattr(oauth, provider, None) is not None


async def _get_or_create_user(
    db: AsyncSession, provider: str, provider_user_id: str, email: str, name: str | None,
) -> User:
    """Trouve ou cree un user OAuth."""
    result = await db.execute(
        select(User).where(
            (User.auth_provider == AuthProvider(provider)) & (User.provider_user_id == provider_user_id)
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # Verifier si un compte local existe deja avec cet email -> on lie les providers
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.auth_provider = AuthProvider(provider)
        user.provider_user_id = provider_user_id
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
        return user

    # Creation d un nouvel utilisateur
    username_base = (name or email.split("@")[0]).lower().replace(" ", "_")[:40]
    username = username_base
    suffix = 1
    while True:
        existing = await db.execute(select(User).where(User.username == username))
        if not existing.scalar_one_or_none():
            break
        suffix += 1
        username = f"{username_base}{suffix}"

    user = User(
        email=email,
        username=username,
        full_name=name,
        auth_provider=AuthProvider(provider),
        provider_user_id=provider_user_id,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    if not _is_provider_configured(provider):
        raise HTTPException(status_code=501, detail=f"OAuth {provider} non configure")
    redirect_uri_map = {
        "google": settings.google_redirect_uri,
        "github": settings.github_redirect_uri,
        "microsoft": settings.microsoft_redirect_uri,
    }
    redirect_uri = redirect_uri_map.get(provider)
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Provider inconnu")
    client = getattr(oauth, provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    if not _is_provider_configured(provider):
        raise HTTPException(status_code=501, detail=f"OAuth {provider} non configure")
    client = getattr(oauth, provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Echec OAuth: {e}")

    # Recuperer infos utilisateur selon le provider
    if provider == "google":
        userinfo: dict[str, Any] = token.get("userinfo") or await client.parse_id_token(request, token)
        provider_user_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name")
    elif provider == "github":
        resp = await client.get("user", token=token)
        profile = resp.json()
        provider_user_id = str(profile["id"])
        email = profile.get("email")
        if not email:
            emails_resp = await client.get("user/emails", token=token)
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else None
        if not email:
            raise HTTPException(status_code=400, detail="Email GitHub non disponible")
        name = profile.get("name")
    elif provider == "microsoft":
        userinfo = await client.parse_id_token(request, token)
        provider_user_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name")
    else:
        raise HTTPException(status_code=400, detail="Provider inconnu")

    user = await _get_or_create_user(db, provider, provider_user_id, email, name)
    access_token = create_access_token(user.id)

    # Rediriger vers le frontend avec le token
    frontend_url = f"{settings.app_url}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_url)