"""Middleware CSRF (double-submit cookie) en pure ASGI pour ne PAS casser les WebSockets.

Le pattern double-submit cookie :
- A la connexion, le serveur pose un cookie supmeal_csrf lisible par le JS.
- Sur les requetes mutantes (POST/PATCH/PUT/DELETE) authentifiees par cookie
  (le cookie httpOnly supmeal_token est envoye automatiquement par le navigateur),
  on exige que le header X-CSRF-Token ait la meme valeur que le cookie supmeal_csrf.

Si l auth est par header Authorization (API client), pas de CSRF : un navigateur
ne peut pas envoyer d Authorization custom depuis un autre site.
"""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
SKIP_PATH_PREFIXES = ("/api/v1/auth/", "/api/v1/cookbooks/ws/")


class CSRFMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # On ne touche PAS aux WebSockets ni au lifespan
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")

        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return
        if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Lire les headers
        headers = dict(scope.get("headers") or [])
        def h(name: str) -> str:
            return headers.get(name.lower().encode("latin-1"), b"").decode("latin-1")

        auth = h("authorization")
        cookie_header = h("cookie")
        has_bearer = auth.lower().startswith("bearer ")
        has_cookie_token = False
        csrf_cookie = ""
        for chunk in cookie_header.split(";"):
            kv = chunk.strip()
            if kv.startswith("supmeal_token="):
                has_cookie_token = True
            if kv.startswith("supmeal_csrf="):
                csrf_cookie = kv[len("supmeal_csrf="):]

        # Pas de cookie auth ou auth par header (API) : on laisse passer
        if not has_cookie_token or has_bearer:
            await self.app(scope, receive, send)
            return

        # Verifier X-CSRF-Token == supmeal_csrf
        csrf_header = h("x-csrf-token")
        if not csrf_header or csrf_header != csrf_cookie:
            response = JSONResponse(
                status_code=403,
                content={"detail": "CSRF token manquant ou invalide"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
