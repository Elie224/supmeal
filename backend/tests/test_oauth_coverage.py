from types import SimpleNamespace

import pytest
from fastapi.responses import RedirectResponse

from app.api.v1.endpoints import oauth as oauth_module
from app.models.user import AuthProvider, User
from app.services.import_export import (
    _parse_minutes,
    _to_float,
    mealie_to_recipe,
)


@pytest.mark.asyncio
async def test_oauth_get_or_create_user_all_paths(db_session):
    first = await oauth_module._get_or_create_user(
        db_session,
        "google",
        "google-001",
        "FIRST@Example.com",
        "<unsafe name>",
    )

    assert first.email == "first@example.com"
    assert first.username == "oauth_user"
    assert first.auth_provider == AuthProvider.GOOGLE
    assert first.provider_user_id == "google-001"

    existing = await oauth_module._get_or_create_user(
        db_session,
        "google",
        "google-001",
        "first@example.com",
        "Other Name",
    )

    assert existing.id == first.id

    local = User(
        email="link@example.com",
        username="local_link",
        auth_provider=AuthProvider.LOCAL,
        is_verified=True,
        is_active=True,
    )
    db_session.add(local)
    await db_session.commit()
    await db_session.refresh(local)

    linked = await oauth_module._get_or_create_user(
        db_session,
        "github",
        "github-linked",
        " LINK@example.com ",
        "Linked User",
    )

    assert linked.id == local.id
    assert linked.auth_provider == AuthProvider.GITHUB
    assert linked.provider_user_id == "github-linked"

    collision = await oauth_module._get_or_create_user(
        db_session,
        "github",
        "github-002",
        "second@example.com",
        "<unsafe name>",
    )

    assert collision.username == "oauth_user2"
    assert collision.email == "second@example.com"


@pytest.mark.asyncio
async def test_oauth_provider_and_login_paths(client, monkeypatch):
    captured = {}

    class FakeLoginClient:
        async def authorize_redirect(
            self,
            request,
            redirect_uri,
        ):
            captured["redirect_uri"] = redirect_uri
            return RedirectResponse(
                "https://provider.example/authorize"
            )

    fake_google = FakeLoginClient()

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=fake_google,
            github=object(),
            facebook=object(),
        ),
    )

    providers = await client.get(
        "/api/v1/auth/oauth/providers"
    )
    assert providers.status_code == 200
    assert providers.json() == {
        "google": True,
        "github": True,
    }

    monkeypatch.setattr(
        oauth_module.settings,
        "app_url",
        "https://frontend.example.com",
    )

    login = await client.get(
        "/api/v1/auth/oauth/google/login",
        headers={
            "x-forwarded-proto": "https",
            "x-forwarded-host": "proxy.example.com",
        },
    )

    assert login.status_code in (302, 307)
    assert captured["redirect_uri"] == (
        "https://frontend.example.com"
        "/api/v1/auth/oauth/google/callback"
    )

    unconfigured = await client.get(
        "/api/v1/auth/oauth/microsoft/login"
    )
    assert unconfigured.status_code == 501

    unknown = await client.get(
        "/api/v1/auth/oauth/facebook/login"
    )
    assert unknown.status_code == 400


@pytest.mark.asyncio
async def test_google_oauth_callback_paths(
    client,
    monkeypatch,
):
    class FakeGoogle:
        async def authorize_access_token(self, request):
            return {}

        async def parse_id_token(
            self,
            request,
            token,
        ):
            return {
                "sub": "google-callback-1",
                "email": "google-callback@example.com",
                "name": "Google Callback",
            }

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=FakeGoogle(),
            github=None,
        ),
    )

    callback = await client.get(
        "/api/v1/auth/oauth/google/callback"
    )

    assert callback.status_code in (302, 307)
    assert "/auth/callback?code=" in (
        callback.headers["location"]
    )
    assert "supmeal_oauth_state=" in (
        callback.headers.get("set-cookie", "")
    )

    # Deuxieme appel : couvre le chemin utilisateur OAuth existant.
    callback_again = await client.get(
        "/api/v1/auth/oauth/google/callback"
    )
    assert callback_again.status_code in (302, 307)

    class GoogleWithoutEmail:
        async def authorize_access_token(self, request):
            return {
                "userinfo": {
                    "sub": "google-no-email",
                    "name": "No Email",
                }
            }

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=GoogleWithoutEmail(),
            github=None,
        ),
    )

    missing_email = await client.get(
        "/api/v1/auth/oauth/google/callback"
    )
    assert missing_email.status_code == 400


@pytest.mark.asyncio
async def test_github_oauth_callback_paths(
    client,
    monkeypatch,
):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class FakeGithub:
        async def authorize_access_token(self, request):
            return {"access_token": "github-token"}

        async def get(self, endpoint, token):
            if endpoint == "user":
                return FakeResponse(
                    {
                        "id": 98765,
                        "email": None,
                        "name": "Github User",
                    }
                )

            return FakeResponse(
                [
                    {
                        "email": "github-callback@example.com",
                        "primary": True,
                        "verified": True,
                    },
                    {
                        "email": "secondary@example.com",
                        "primary": False,
                        "verified": True,
                    },
                ]
            )

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=None,
            github=FakeGithub(),
        ),
    )

    callback = await client.get(
        "/api/v1/auth/oauth/github/callback"
    )

    assert callback.status_code in (302, 307)
    assert "/auth/callback?code=" in (
        callback.headers["location"]
    )

    class GithubWithoutEmail(FakeGithub):
        async def get(self, endpoint, token):
            if endpoint == "user":
                return FakeResponse(
                    {
                        "id": 99999,
                        "email": None,
                        "name": "No Email",
                    }
                )

            return FakeResponse(
                [
                    {
                        "email": "unverified@example.com",
                        "primary": True,
                        "verified": False,
                    }
                ]
            )

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=None,
            github=GithubWithoutEmail(),
        ),
    )

    missing_email = await client.get(
        "/api/v1/auth/oauth/github/callback"
    )
    assert missing_email.status_code == 400

    class BrokenGithub:
        async def authorize_access_token(self, request):
            raise RuntimeError("OAuth provider failed")

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=None,
            github=BrokenGithub(),
        ),
    )

    failed = await client.get(
        "/api/v1/auth/oauth/github/callback"
    )
    assert failed.status_code == 400
    assert "Echec OAuth" in failed.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_callback_unknown_provider(
    client,
    monkeypatch,
):
    class FakeUnknown:
        async def authorize_access_token(self, request):
            return {"access_token": "token"}

    monkeypatch.setattr(
        oauth_module,
        "oauth",
        SimpleNamespace(
            google=None,
            github=None,
            facebook=FakeUnknown(),
        ),
    )

    response = await client.get(
        "/api/v1/auth/oauth/facebook/callback"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provider inconnu"


def test_import_export_conversion_helpers():
    assert _parse_minutes(None) == 0
    assert _parse_minutes("") == 0
    assert _parse_minutes(15) == 15
    assert _parse_minutes(12.8) == 12

    assert _parse_minutes("PT15M") == 15
    assert _parse_minutes("PT2H") == 120
    assert _parse_minutes("PT1H30M") == 90
    assert _parse_minutes("45 min") == 45
    assert _parse_minutes("unknown") == 0

    assert _to_float(None) is None
    assert _to_float("3.5") == 3.5
    assert _to_float(2) == 2.0
    assert _to_float("invalid") is None

    converted = mealie_to_recipe(
        {
            "name": "Mealie coverage",
            "description": "Test",
            "orgURL": "https://example.com/recipe",
            "prepTime": "PT1H15M",
            "cookTime": "30 min",
            "recipeServings": 6,
            "image": "/image.jpg",
            "recipeIngredient": [
                {
                    "note": "Rice",
                    "quantity": "2.5",
                    "unit": {
                        "name": "kg",
                    },
                },
                {
                    "note": "Water",
                    "quantity": "invalid",
                    "unit": "litre",
                },
            ],
            "recipeInstructions": [
                {
                    "text": "Step one\nStep two",
                }
            ],
            "tags": [
                {"name": "Dinner"},
                {"name": ""},
            ],
        }
    )

    assert converted["title"] == "Mealie coverage"
    assert converted["prep_time_minutes"] == 75
    assert converted["cook_time_minutes"] == 30
    assert converted["servings"] == 6

    assert converted["ingredients"][0] == {
        "name": "Rice",
        "unit": "kg",
        "quantity": 2.5,
    }

    assert converted["ingredients"][1] == {
        "name": "Water",
        "unit": None,
        "quantity": None,
    }

    assert converted["steps"] == [
        {
            "content": "Step one\nStep two",
        }
    ]

    assert converted["tag_names"] == [
        "dinner",
    ]


@pytest.mark.asyncio
async def test_recipe_permission_helper_short_paths():
    from app.api.v1.endpoints import recipes as recipes_module

    private_recipe = SimpleNamespace(
        is_public=False,
        owner_id=7,
        cookbook_id=None,
    )

    assert (
        await recipes_module._can_view(
            private_recipe,
            None,
            None,
        )
        is False
    )

    assert (
        await recipes_module._can_view(
            private_recipe,
            7,
            None,
        )
        is True
    )

    assert (
        await recipes_module._can_edit(
            private_recipe,
            8,
            None,
        )
        is False
    )

    public_recipe = SimpleNamespace(
        is_public=True,
        owner_id=7,
        cookbook_id=None,
    )

    assert (
        await recipes_module._can_view(
            public_recipe,
            None,
            None,
        )
        is True
    )


def test_parse_minutes_whitespace_only():
    assert _parse_minutes("   ") == 0


@pytest.mark.asyncio
async def test_recipe_owner_can_edit_short_path():
    from app.api.v1.endpoints import recipes as recipes_module

    recipe = SimpleNamespace(
        owner_id=42,
        cookbook_id=None,
    )

    assert (
        await recipes_module._can_edit(
            recipe,
            42,
            None,
        )
        is True
    )


@pytest.mark.asyncio
async def test_recipe_cookbook_editor_can_edit(monkeypatch):
    from app.api.v1.endpoints import recipes as recipes_module

    recipe = SimpleNamespace(
        owner_id=1,
        cookbook_id=77,
    )

    async def fake_cookbook_role(db, cookbook_id, user_id):
        assert cookbook_id == 77
        assert user_id == 2
        return recipes_module.CookbookRole.EDITOR

    monkeypatch.setattr(
        recipes_module,
        "_cookbook_role",
        fake_cookbook_role,
    )

    assert (
        await recipes_module._can_edit(
            recipe,
            2,
            None,
        )
        is True
    )
