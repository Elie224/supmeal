import pytest
from sqlalchemy import func, select

from app.core import pwned
from app.core.security import create_access_token, hash_password
from app.models.recipe import (
    RecipeFavorite,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
    Tag,
)
from app.models.user import AuthProvider, User
from app.services.recipe_service import (
    create_recipe,
    rebuild_search_vector,
    update_recipe,
)


async def _register(
    client,
    email: str,
    username: str,
    password: str = "SupMeal!Final2026",
):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return (
        {"Authorization": f"Bearer {body['access_token']}"},
        body,
    )


def test_pwned_network_cache_and_fail_open(monkeypatch):
    pwned._cache.clear()
    pwned._suffixes_map.clear()

    password = "CompromisedPassword123!"
    digest = pwned._hash_pw(password)
    suffix = digest[5:]

    class FakeResponse:
        status_code = 200
        text = f"{suffix}:999\nBROKEN\nABC:1:2"

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get(self, url, headers):
            assert url.startswith(pwned._HIBP_URL)
            assert headers == {"Add-Padding": "true"}
            return FakeResponse()

    monkeypatch.setattr(
        pwned.httpx,
        "Client",
        FakeClient,
    )

    assert pwned.is_pwned(password) is True

    class MustNotBeCalled:
        def __init__(self, timeout):
            raise AssertionError("Le cache devait etre utilise")

    monkeypatch.setattr(
        pwned.httpx,
        "Client",
        MustNotBeCalled,
    )

    assert pwned.is_pwned(password) is True

    pwned._cache.clear()
    pwned._suffixes_map.clear()

    class Non200Response:
        status_code = 503
        text = ""

    class Non200Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get(self, url, headers):
            return Non200Response()

    monkeypatch.setattr(
        pwned.httpx,
        "Client",
        Non200Client,
    )

    assert pwned.is_pwned("AnotherPassword123!") is False

    pwned._cache.clear()
    pwned._suffixes_map.clear()

    class BrokenClient:
        def __init__(self, timeout):
            raise RuntimeError("network unavailable")

    monkeypatch.setattr(
        pwned.httpx,
        "Client",
        BrokenClient,
    )

    assert pwned.is_pwned("NetworkFailure123!") is False
    assert pwned.is_pwned("") is False
    assert pwned.is_pwned("abc") is False


@pytest.mark.asyncio
async def test_recipe_service_create_update_and_search_vector(
    client,
    db_session,
):
    _, body = await _register(
        client,
        "service-final@example.com",
        "service_final",
    )
    user_id = body["user"]["id"]

    tag = Tag(
        name="service-tag",
        category="type",
    )
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)

    recipe = await create_recipe(
        db_session,
        owner_id=user_id,
        title="Service coverage",
        description="Description service",
        prep_time_minutes="5",
        cook_time_minutes=None,
        servings="",
        difficulty="easy",
        cuisine_type="african",
        ingredients=[
            {
                "name": "rice",
                "quantity": 1,
                "unit": "kg",
            },
            {
                "name": "water",
                "quantity": 2,
                "unit": "l",
                "position": 4,
            },
        ],
        steps=[
            {
                "content": "",
            },
            {
                "content": "Cook everything",
            },
        ],
        tag_ids=[tag.id],
        tag_names=[
            "fresh",
            " ",
        ],
        favorite_user_id=user_id,
    )

    await db_session.commit()

    assert recipe.id is not None
    assert recipe.prep_time_minutes == 5
    assert recipe.cook_time_minutes == 0
    assert recipe.servings == 4

    ingredients_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe.id)
    )
    assert ingredients_count == 2

    steps_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeStep)
        .where(RecipeStep.recipe_id == recipe.id)
    )
    assert steps_count == 1

    tags_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeTag)
        .where(RecipeTag.recipe_id == recipe.id)
    )
    assert tags_count == 2

    favorite_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeFavorite)
        .where(
            (RecipeFavorite.recipe_id == recipe.id)
            & (RecipeFavorite.user_id == user_id)
        )
    )
    assert favorite_count == 1

    await update_recipe(
        db_session,
        recipe=recipe,
        fields={
            "title": "Service coverage updated",
            "description": "Updated service",
        },
        ingredients=[
            {
                "name": "tomato",
                "quantity": 3,
                "unit": "piece",
            },
            {
                "name": "onion",
                "quantity": 1,
                "unit": "piece",
            },
        ],
        steps=[
            {
                "content": "Cut vegetables",
            },
            {
                "content": " ",
            },
            {
                "content": "Cook slowly",
            },
        ],
        tag_ids=[tag.id],
    )

    await db_session.commit()

    ingredients_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe.id)
    )
    assert ingredients_count == 2

    steps_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeStep)
        .where(RecipeStep.recipe_id == recipe.id)
    )
    assert steps_count == 2

    tags_count = await db_session.scalar(
        select(func.count())
        .select_from(RecipeTag)
        .where(RecipeTag.recipe_id == recipe.id)
    )
    assert tags_count == 1

    await rebuild_search_vector(
        db_session,
        recipe.id,
    )

    await rebuild_search_vector(
        db_session,
        999999,
    )


@pytest.mark.asyncio
async def test_auth_reactivation_disabled_and_oauth_password(
    client,
    db_session,
):
    inactive = User(
        email="reactivate-final@example.com",
        username="old_reactivate",
        full_name="Old name",
        hashed_password=hash_password("OldPassword1!"),
        auth_provider=AuthProvider.LOCAL,
        is_verified=False,
        is_active=False,
    )

    db_session.add(inactive)
    await db_session.commit()
    await db_session.refresh(inactive)

    reactivated = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reactivate-final@example.com",
            "username": "new_reactivate",
            "full_name": "New name",
            "password": "NewPassword2!",
            "dietary_preferences": "vegetarian",
            "allergies": "none",
            "favorite_cuisines": "african",
            "default_servings": 5,
        },
    )

    assert reactivated.status_code == 201, reactivated.text
    assert reactivated.json()["user"]["username"] == "new_reactivate"
    assert reactivated.json()["user"]["is_verified"] is True
    assert reactivated.json()["user"]["is_active"] is True
    assert reactivated.json()["user"]["default_servings"] == 5

    disabled = User(
        email="disabled-final@example.com",
        username="disabled_final",
        hashed_password=hash_password("DisabledPassword1!"),
        auth_provider=AuthProvider.LOCAL,
        is_verified=True,
        is_active=False,
    )

    oauth_user = User(
        email="oauth-final@example.com",
        username="oauth_final",
        hashed_password=None,
        auth_provider=AuthProvider.GOOGLE,
        provider_user_id="google-final-1",
        is_verified=True,
        is_active=True,
    )

    db_session.add_all(
        [
            disabled,
            oauth_user,
        ]
    )
    await db_session.commit()
    await db_session.refresh(disabled)
    await db_session.refresh(oauth_user)

    disabled_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": disabled.email,
            "password": "DisabledPassword1!",
        },
    )
    assert disabled_login.status_code == 403

    oauth_token = create_access_token(oauth_user.id)
    oauth_headers = {
        "Authorization": f"Bearer {oauth_token}"
    }

    oauth_change = await client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "Anything1!",
            "new_password": "AnythingElse2!",
        },
        headers=oauth_headers,
    )
    assert oauth_change.status_code == 400


@pytest.mark.asyncio
async def test_csv_export_and_import_validation_paths(client):
    headers, _ = await _register(
        client,
        "export-final@example.com",
        "export_final",
    )

    recipe = await client.post(
        "/api/v1/recipes",
        json={
            "title": "=FORMULA",
            "description": "+danger",
            "source_url": "-source",
            "servings": 2,
            "prep_time_minutes": 5,
            "cook_time_minutes": 10,
            "ingredients": [
                {
                    "name": "@ingredient",
                    "quantity": 2,
                    "unit": "+kg",
                    "position": 0,
                }
            ],
            "steps": [
                {
                    "content": "=step",
                    "position": 1,
                }
            ],
        },
        headers=headers,
    )
    assert recipe.status_code == 201, recipe.text

    exported = await client.get(
        "/api/v1/import-export/csv",
        headers=headers,
    )

    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]

    csv_text = exported.text
    assert "'=FORMULA" in csv_text
    assert "'+danger" in csv_text
    assert "'@ingredient" in csv_text
    assert "'+kg" in csv_text
    assert "'=step" in csv_text

    invalid_json = await client.post(
        "/api/v1/import-export/json",
        files={
            "file": (
                "invalid.json",
                b"{invalid",
                "application/json",
            )
        },
        headers=headers,
    )
    assert invalid_json.status_code == 400

    bad_csv = "\n".join(
        [
            (
                "title,description,servings,prep_time,cook_time,"
                "ingredient,quantity,unit,step,tags,source"
            ),
            "BadInt,desc,abc,1,2,rice,1,kg,,,",
            "BadFloat,desc,4,1,2,rice,abc,kg,,,",
            ",desc,4,1,2,rice,1,kg,,,",
        ]
    )

    imported = await client.post(
        "/api/v1/import-export/csv",
        files={
            "file": (
                "bad.csv",
                bad_csv.encode("utf-8"),
                "text/csv",
            )
        },
        headers=headers,
    )

    assert imported.status_code == 201, imported.text
    payload = imported.json()
    assert payload["imported_recipes"] == 0
    assert payload["ignored_rows"] == 3
    assert len(payload["errors"]) == 2


@pytest.mark.asyncio
async def test_shopping_error_and_full_update_paths(client):
    owner_headers, _ = await _register(
        client,
        "shopping-final@example.com",
        "shopping_final",
    )

    outsider_headers, _ = await _register(
        client,
        "shopping-outsider-final@example.com",
        "shopping_outsider_final",
    )

    no_plan = await client.post(
        "/api/v1/shopping/generate",
        json={
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
        },
        headers=owner_headers,
    )
    assert no_plan.status_code == 404

    cookbook = await client.post(
        "/api/v1/cookbooks",
        json={
            "name": "Shopping private cookbook",
        },
        headers=owner_headers,
    )
    assert cookbook.status_code == 201
    cookbook_id = cookbook.json()["id"]

    forbidden_generate = await client.post(
        "/api/v1/shopping/generate",
        json={
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
            "cookbook_id": cookbook_id,
        },
        headers=outsider_headers,
    )
    assert forbidden_generate.status_code == 403

    recipe = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Shopping final recipe",
            "servings": 2,
            "ingredients": [
                {
                    "name": "Rice",
                    "quantity": 1,
                    "unit": "KG",
                    "position": 0,
                }
            ],
            "steps": [
                {
                    "content": "Cook",
                    "position": 0,
                }
            ],
        },
        headers=owner_headers,
    )
    assert recipe.status_code == 201

    plan = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe.json()["id"],
            "planned_date": "2026-09-10",
            "meal_slot": "dinner",
            "servings": 4,
        },
        headers=owner_headers,
    )
    assert plan.status_code == 201

    generated = await client.post(
        "/api/v1/shopping/generate",
        json={
            "start_date": "2026-09-10",
            "end_date": "2026-09-10",
            "name": "Initial shopping",
        },
        headers=owner_headers,
    )
    assert generated.status_code == 201
    list_id = generated.json()["id"]

    forbidden_detail = await client.get(
        f"/api/v1/shopping/{list_id}",
        headers=outsider_headers,
    )
    assert forbidden_detail.status_code == 404

    updated_list = await client.patch(
        f"/api/v1/shopping/{list_id}",
        json={
            "name": "  Updated shopping  ",
            "is_completed": False,
        },
        headers=owner_headers,
    )
    assert updated_list.status_code == 200
    assert updated_list.json()["name"] == "Updated shopping"

    added = await client.post(
        f"/api/v1/shopping/{list_id}/items",
        json={
            "name": "  MILK  ",
            "quantity": 1,
            "unit": " L ",
            "is_checked": False,
        },
        headers=owner_headers,
    )
    assert added.status_code == 201
    item_id = added.json()["id"]
    assert added.json()["name"] == "milk"
    assert added.json()["unit"] == "l"

    updated_item = await client.patch(
        f"/api/v1/shopping/{list_id}/items/{item_id}",
        json={
            "name": "  BREAD  ",
            "quantity": 2.5,
            "unit": " PIECE ",
            "is_checked": True,
        },
        headers=owner_headers,
    )
    assert updated_item.status_code == 200
    assert updated_item.json()["name"] == "bread"
    assert updated_item.json()["quantity"] == 2.5
    assert updated_item.json()["unit"] == "piece"
    assert updated_item.json()["is_checked"] is True

    forbidden_item = await client.patch(
        f"/api/v1/shopping/{list_id}/items/{item_id}",
        json={
            "is_checked": False,
        },
        headers=outsider_headers,
    )
    assert forbidden_item.status_code == 404
