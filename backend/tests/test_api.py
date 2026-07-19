"""Tests d'integration : auth, recettes, cookbooks."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.cookbook import CookbookInvitation


async def _auth_headers(client, email: str, username: str, password: str) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert reg.status_code in (200, 201), reg.text
    token = reg.json().get("access_token")
    if not token:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "username": "alice",
            "password": "Sup3rSecret!",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["email"] == "alice@example.com"
    assert "access_token" in data

    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "Sup3rSecret!"},
    )
    assert r2.status_code == 200
    assert "access_token" in r2.json()


@pytest.mark.asyncio
async def test_register_duplicate(client):
    payload = {"email": "bob@example.com", "username": "bob", "password": "Motdepasse1"}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_recipe_and_favorite(client):
    # Register
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "charlie@example.com", "username": "charlie", "password": "Motdepasse1"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create recipe
    payload = {
        "title": "Tarte tatin",
        "description": "Classique",
        "servings": 6,
        "prep_time_minutes": 20,
        "cook_time_minutes": 45,
        "difficulty": "moyen",
        "cuisine_type": "francaise",
        "ingredients": [
            {"name": "pommes", "quantity": 6, "unit": None, "position": 0},
            {"name": "sucre", "quantity": 200, "unit": "g", "position": 1},
            {"name": "beurre", "quantity": 100, "unit": "g", "position": 2},
        ],
        "steps": [
            {"content": "Prechauffer le four a 180 degres.", "position": 0},
            {"content": "Couper les pommes.", "position": 1},
        ],
        "tag_ids": [],
    }
    r = await client.post("/api/v1/recipes", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    recipe_id = r.json()["id"]

    # Read
    r = await client.get(f"/api/v1/recipes/{recipe_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Tarte tatin"
    assert len(r.json()["ingredients"]) == 3

    # Favorite
    r = await client.post(f"/api/v1/recipes/{recipe_id}/favorite", headers=headers)
    assert r.status_code == 200
    assert r.json()["is_favorite"] is True

    # List with favorites_only
    r = await client.get("/api/v1/recipes?favorites_only=true", headers=headers)
    assert r.status_code == 200
    assert any(rec["id"] == recipe_id for rec in r.json())


@pytest.mark.asyncio
async def test_favorites_only_filter_is_applied_before_pagination(client):
    headers = await _auth_headers(
        client,
        "fav-page@example.com",
        "fav_page",
        "SupMeal!FavPage#2026",
    )

    first_recipe_id: int | None = None
    for i in range(25):
        created = await client.post(
            "/api/v1/recipes",
            json={
                "title": f"Recette pagination {i}",
                "ingredients": [{"name": "ing", "position": 0}],
                "steps": [{"content": "step", "position": 0}],
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        if i == 0:
            first_recipe_id = created.json()["id"]

    assert first_recipe_id is not None
    fav = await client.post(f"/api/v1/recipes/{first_recipe_id}/favorite", headers=headers)
    assert fav.status_code == 200, fav.text

    # Le favori est vieux (hors premiere page generale), mais doit apparaitre
    # grace au filtrage SQL avant offset/limit.
    listed = await client.get(
        "/api/v1/recipes?favorites_only=true&skip=0&limit=20",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert len(payload) >= 1
    assert any(item["id"] == first_recipe_id for item in payload)


@pytest.mark.asyncio
async def test_cookbook_member_roles(client):
    # Create owner
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "username": "owner", "password": "Motdepasse1"},
    )
    owner_token = r.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Create another user
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "guest@example.com", "username": "guest", "password": "Motdepasse1"},
    )
    guest_token = r.json()["access_token"]
    guest_headers = {"Authorization": f"Bearer {guest_token}"}

    # Create cookbook
    r = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Famille", "description": "Recettes de famille"},
        headers=owner_headers,
    )
    assert r.status_code == 201
    cb_id = r.json()["id"]

    # Add guest as reader
    r = await client.post(
        f"/api/v1/cookbooks/{cb_id}/members",
        json={"user_email": "guest@example.com", "role": "reader"},
        headers=owner_headers,
    )
    assert r.status_code == 201

    # Guest can read
    r = await client.get(f"/api/v1/cookbooks/{cb_id}", headers=guest_headers)
    assert r.status_code == 200

    # Guest can post message (discussion ouverte a tous les membres)
    r = await client.post(
        f"/api/v1/cookbooks/{cb_id}/messages",
        json={"content": "Hello"},
        headers=guest_headers,
    )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_import_export_json(client):
    headers = await _auth_headers(
        client,
        "ex@example.com",
        "ex_user",
        "Motdepasse1",
    )

    # Create 2 recipes
    for i in range(2):
        await client.post(
            "/api/v1/recipes",
            json={
                "title": f"Recette {i}",
                "ingredients": [{"name": "ing1", "position": 0}],
                "steps": [{"content": "Faire cuire", "position": 0}],
            },
            headers=headers,
        )

    # Export
    r = await client.get("/api/v1/import-export/json", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["format"] == "supmeal-json"
    assert len(data["recipes"]) == 2


@pytest.mark.asyncio
async def test_filter_recipes_by_tag_category(client):
    # Register
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "cat@example.com", "username": "cat", "password": "Motdepasse1"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create tags in different categories
    t1 = await client.post(
        "/api/v1/tags",
        json={"name": "vegan", "category": "diet"},
        headers=headers,
    )
    t2 = await client.post(
        "/api/v1/tags",
        json={"name": "italian", "category": "cuisine"},
        headers=headers,
    )
    assert t1.status_code == 201
    assert t2.status_code == 201
    diet_tag_id = t1.json()["id"]
    cuisine_tag_id = t2.json()["id"]

    # Create recipes with tags
    r1 = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Salade vegan",
            "ingredients": [{"name": "salade", "position": 0}],
            "steps": [{"content": "Melanger", "position": 0}],
            "tag_ids": [diet_tag_id],
        },
        headers=headers,
    )
    r2 = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Pasta italiana",
            "ingredients": [{"name": "pates", "position": 0}],
            "steps": [{"content": "Cuire", "position": 0}],
            "tag_ids": [cuisine_tag_id],
        },
        headers=headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201

    # Filter by category
    filtered = await client.get("/api/v1/recipes?tag_category=diet", headers=headers)
    assert filtered.status_code == 200
    titles = {item["title"] for item in filtered.json()}
    assert "Salade vegan" in titles
    assert "Pasta italiana" not in titles


@pytest.mark.asyncio
async def test_cookbook_collaborative_meal_plans_permissions(client):
    # Create owner, member and outsider
    owner = await client.post(
        "/api/v1/auth/register",
        json={"email": "plan-owner@example.com", "username": "plan_owner", "password": "Motdepasse1"},
    )
    member = await client.post(
        "/api/v1/auth/register",
        json={"email": "plan-member@example.com", "username": "plan_member", "password": "Motdepasse1"},
    )
    outsider = await client.post(
        "/api/v1/auth/register",
        json={"email": "plan-outsider@example.com", "username": "plan_outsider", "password": "Motdepasse1"},
    )
    owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    member_headers = {"Authorization": f"Bearer {member.json()['access_token']}"}
    outsider_headers = {"Authorization": f"Bearer {outsider.json()['access_token']}"}

    # Create cookbook and invite member as commentator
    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Planning famille", "description": "Collab"},
        headers=owner_headers,
    )
    assert cb.status_code == 201
    cb_id = cb.json()["id"]

    add_member = await client.post(
        f"/api/v1/cookbooks/{cb_id}/members",
        json={"user_email": "plan-member@example.com", "role": "commentator"},
        headers=owner_headers,
    )
    assert add_member.status_code == 201

    # Create a recipe in the cookbook
    recipe = await client.post(
        f"/api/v1/cookbooks/{cb_id}/recipes",
        json={
            "title": "Gratin",
            "ingredients": [{"name": "pommes de terre", "position": 0}],
            "steps": [{"content": "Cuire au four", "position": 0}],
        },
        headers=owner_headers,
    )
    assert recipe.status_code == 201
    recipe_id = recipe.json()["id"]

    # Member can create collaborative plan in cookbook
    create_plan = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "cookbook_id": cb_id,
            "planned_date": "2026-07-10",
            "meal_slot": "dinner",
            "servings": 4,
        },
        headers=member_headers,
    )
    assert create_plan.status_code == 201, create_plan.text

    # Outsider cannot create plan on cookbook
    denied_create = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "cookbook_id": cb_id,
            "planned_date": "2026-07-11",
            "meal_slot": "lunch",
            "servings": 4,
        },
        headers=outsider_headers,
    )
    assert denied_create.status_code == 403

    # Owner can list cookbook plans
    owner_list = await client.get(f"/api/v1/meal-plans?cookbook_id={cb_id}", headers=owner_headers)
    assert owner_list.status_code == 200
    assert any(p["recipe_id"] == recipe_id for p in owner_list.json())

    # Outsider cannot list cookbook plans
    outsider_list = await client.get(f"/api/v1/meal-plans?cookbook_id={cb_id}", headers=outsider_headers)
    assert outsider_list.status_code == 403


@pytest.mark.asyncio
async def test_shopping_list_lifecycle(client):
    password = "SupMeal!Test#2026A"
    # User + auth
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "shop@example.com", "username": "shop", "password": password},
    )
    assert reg.status_code in (200, 201), reg.text
    token = reg.json().get("access_token")
    if not token:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "shop@example.com", "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Recipe
    recipe = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Soupe",
            "servings": 2,
            "ingredients": [
                {"name": "carotte", "quantity": 2, "unit": None, "position": 0},
                {"name": "eau", "quantity": 1, "unit": "l", "position": 1},
            ],
            "steps": [{"content": "Cuire", "position": 0}],
        },
        headers=headers,
    )
    assert recipe.status_code == 201, recipe.text
    recipe_id = recipe.json()["id"]

    # Meal plan entry
    plan = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "planned_date": "2026-07-12",
            "meal_slot": "dinner",
            "servings": 4,
        },
        headers=headers,
    )
    assert plan.status_code == 201, plan.text

    # Generate shopping list
    generated = await client.post(
        "/api/v1/shopping/generate",
        json={
            "start_date": "2026-07-12",
            "end_date": "2026-07-12",
            "name": "Courses test",
        },
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    list_id = generated.json()["id"]

    # List + detail
    listed = await client.get("/api/v1/shopping", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == list_id for item in listed.json())

    detail = await client.get(f"/api/v1/shopping/{list_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["items"]) >= 1
    first_item_id = detail.json()["items"][0]["id"]

    # Update list
    updated_list = await client.patch(
        f"/api/v1/shopping/{list_id}",
        json={"is_completed": True},
        headers=headers,
    )
    assert updated_list.status_code == 200
    assert updated_list.json()["is_completed"] is True

    # Add item
    added_item = await client.post(
        f"/api/v1/shopping/{list_id}/items",
        json={"name": "pain", "quantity": 1, "unit": "piece"},
        headers=headers,
    )
    assert added_item.status_code == 201
    added_item_id = added_item.json()["id"]

    # Toggle item
    toggled = await client.patch(
        f"/api/v1/shopping/{list_id}/items/{first_item_id}",
        json={"is_checked": True},
        headers=headers,
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_checked"] is True

    # Delete item
    deleted_item = await client.delete(
        f"/api/v1/shopping/{list_id}/items/{added_item_id}", headers=headers
    )
    assert deleted_item.status_code == 204

    # Delete list
    deleted_list = await client.delete(f"/api/v1/shopping/{list_id}", headers=headers)
    assert deleted_list.status_code == 204


@pytest.mark.asyncio
async def test_avatar_upload(client):
    password = "SupMeal!Avatar#2026B"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "ava@example.com", "username": "ava", "password": password},
    )
    assert reg.status_code in (200, 201), reg.text
    token = reg.json().get("access_token")
    if not token:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "ava@example.com", "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1x1 PNG valide (signature PNG + contenu minimal)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    upload = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    avatar_url = upload.json().get("avatar_url")
    assert avatar_url and avatar_url.startswith("/uploads/")

    fetched = await client.get(avatar_url)
    assert fetched.status_code == 200


def test_websocket_chat_broadcast(engine):
    with TestClient(app) as tc:
        owner_reg = tc.post(
            "/api/v1/auth/register",
            json={
                "email": "ws-owner@example.com",
                "username": "ws_owner",
                "password": "SupMeal!WsOwner#2026",
            },
        )
        assert owner_reg.status_code in (200, 201), owner_reg.text
        owner_token = owner_reg.json()["access_token"]

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        cb = tc.post(
            "/api/v1/cookbooks",
            json={"name": "WS Club", "description": "chat"},
            headers=owner_headers,
        )
        assert cb.status_code == 201, cb.text
        cb_id = cb.json()["id"]

        with tc.websocket_connect(
            f"/api/v1/cookbooks/{cb_id}/ws",
            subprotocols=[f"bearer.{owner_token}"],
        ) as ws_owner:
            ws_owner.send_json({"content": "Bonjour equipe"})
            recv_owner = ws_owner.receive_json()
            assert recv_owner["content"] == "Bonjour equipe"

        # Verifie la persistence du message via endpoint HTTP
        listed = tc.get(f"/api/v1/cookbooks/{cb_id}/messages", headers=owner_headers)
        assert listed.status_code == 200
        assert any(msg["content"] == "Bonjour equipe" for msg in listed.json())


@pytest.mark.asyncio
async def test_comment_permissions_fine_grained(client):
    owner_headers = await _auth_headers(
        client,
        "c-owner@example.com",
        "c_owner",
        "SupMeal!CommentOwner#2026",
    )
    commentator_headers = await _auth_headers(
        client,
        "c-comment@example.com",
        "c_comment",
        "SupMeal!Commentator#2026",
    )
    reader_headers = await _auth_headers(
        client,
        "c-reader@example.com",
        "c_reader",
        "SupMeal!CommentReader#2026",
    )
    outsider_headers = await _auth_headers(
        client,
        "c-outsider@example.com",
        "c_outsider",
        "SupMeal!CommentOut#2026",
    )

    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Commentaires", "description": "roles"},
        headers=owner_headers,
    )
    assert cb.status_code == 201
    cb_id = cb.json()["id"]

    add_commentator = await client.post(
        f"/api/v1/cookbooks/{cb_id}/members",
        json={"user_email": "c-comment@example.com", "role": "commentator"},
        headers=owner_headers,
    )
    assert add_commentator.status_code == 201

    add_reader = await client.post(
        f"/api/v1/cookbooks/{cb_id}/members",
        json={"user_email": "c-reader@example.com", "role": "reader"},
        headers=owner_headers,
    )
    assert add_reader.status_code == 201

    recipe = await client.post(
        f"/api/v1/cookbooks/{cb_id}/recipes",
        json={
            "title": "Recette com",
            "ingredients": [{"name": "sel", "position": 0}],
            "steps": [{"content": "Melanger", "position": 0}],
        },
        headers=owner_headers,
    )
    assert recipe.status_code == 201
    recipe_id = recipe.json()["id"]

    c1 = await client.post(
        f"/api/v1/recipes/{recipe_id}/comments",
        json={"content": "Super idee"},
        headers=commentator_headers,
    )
    assert c1.status_code == 201, c1.text
    comment_id = c1.json()["id"]

    c2 = await client.post(
        f"/api/v1/recipes/{recipe_id}/comments",
        json={"content": "Je suis reader"},
        headers=reader_headers,
    )
    assert c2.status_code == 403

    c3 = await client.post(
        f"/api/v1/recipes/{recipe_id}/comments",
        json={"content": "Je suis outsider"},
        headers=outsider_headers,
    )
    assert c3.status_code == 403

    c4 = await client.delete(
        f"/api/v1/recipes/{recipe_id}/comments/{comment_id}",
        headers=owner_headers,
    )
    assert c4.status_code == 403

    c5 = await client.delete(
        f"/api/v1/recipes/{recipe_id}/comments/{comment_id}",
        headers=commentator_headers,
    )
    assert c5.status_code == 204


@pytest.mark.asyncio
async def test_import_csv_exhaustive(client):
    headers = await _auth_headers(
        client,
        "csv@example.com",
        "csv_user",
        "SupMeal!CsvImport#2026",
    )

    csv_content = "\n".join(
        [
            "title,description,servings,prep_time,cook_time,ingredient,quantity,unit,step,tags,source",
            "Lasagne,Plat familial,6,30,45,pates,500,g,,italien;gratin,https://example.com/lasagne",
            "Lasagne,Plat familial,6,30,45,boeuf,400,g,,italien;gratin,https://example.com/lasagne",
            "Lasagne,Plat familial,6,30,45,,,,Monter les couches,italien;gratin,https://example.com/lasagne",
            "Soup,Entree simple,2,10,20,eau,1,l,,healthy,",
            "Soup,Entree simple,2,10,20,,,,Faire bouillir,healthy,",
        ]
    )
    upload = await client.post(
        "/api/v1/import-export/csv",
        files={"file": ("import.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["imported_recipes"] == 2

    listed = await client.get("/api/v1/recipes?limit=100", headers=headers)
    assert listed.status_code == 200
    titles = {r["title"] for r in listed.json()}
    assert "Lasagne" in titles
    assert "Soup" in titles


@pytest.mark.asyncio
async def test_import_mealie_json_exhaustive(client):
    headers = await _auth_headers(
        client,
        "mealie@example.com",
        "mealie_user",
        "SupMeal!MealieImport#2026",
    )

    mealie_payload = {
        "format": "mealie",
        "recipes": [
            {
                "name": "Curry Maison",
                "description": "epice",
                "orgURL": "https://example.com/curry",
                "prepTime": "PT15M",
                "cookTime": "PT35M",
                "recipeServings": 4,
                "image": "https://img.example/curry.jpg",
                "recipeIngredient": [
                    {"note": "poulet", "quantity": "500", "unit": {"name": "g"}},
                    {"note": "lait de coco", "quantity": "40", "unit": {"name": "cl"}},
                ],
                "recipeInstructions": [
                    {"text": "Faire revenir"},
                    {"text": "Laisser mijoter"},
                ],
                "tags": [{"name": "Curry"}, {"name": "Dinner"}],
            }
        ],
    }

    upload = await client.post(
        "/api/v1/import-export/json",
        files={
            "file": (
                "mealie.json",
                json.dumps(mealie_payload).encode("utf-8"),
                "application/json",
            )
        },
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["imported_recipes"] == 1

    listed = await client.get("/api/v1/recipes?search=Curry&limit=20", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    recipe_id = listed.json()[0]["id"]

    detail = await client.get(f"/api/v1/recipes/{recipe_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Curry Maison"
    assert body["prep_time_minutes"] == 15
    assert body["cook_time_minutes"] == 35
    assert any(i["name"] == "poulet" for i in body["ingredients"])
    assert any(s["content"] == "Faire revenir" for s in body["steps"])
    assert any(t["name"] == "curry" for t in body["tags"])


@pytest.mark.asyncio
async def test_personal_favorites_are_isolated_between_users(client):
    owner_headers = await _auth_headers(
        client,
        "fav-owner@example.com",
        "fav_owner",
        "SupMeal!FavOwner#2026",
    )
    member_headers = await _auth_headers(
        client,
        "fav-member@example.com",
        "fav_member",
        "SupMeal!FavMember#2026",
    )

    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Fav Shared", "description": "test"},
        headers=owner_headers,
    )
    assert cb.status_code == 201, cb.text
    cb_id = cb.json()["id"]

    add_member = await client.post(
        f"/api/v1/cookbooks/{cb_id}/members",
        json={"user_email": "fav-member@example.com", "role": "reader"},
        headers=owner_headers,
    )
    assert add_member.status_code == 201, add_member.text

    recipe = await client.post(
        f"/api/v1/cookbooks/{cb_id}/recipes",
        json={
            "title": "Shared Favorite",
            "ingredients": [{"name": "tomate", "position": 0}],
            "steps": [{"content": "couper", "position": 0}],
        },
        headers=owner_headers,
    )
    assert recipe.status_code == 201, recipe.text
    recipe_id = recipe.json()["id"]

    toggle = await client.post(f"/api/v1/recipes/{recipe_id}/favorite", headers=member_headers)
    assert toggle.status_code == 200, toggle.text
    assert toggle.json()["is_favorite"] is True

    member_favs = await client.get("/api/v1/recipes?favorites_only=true", headers=member_headers)
    assert member_favs.status_code == 200, member_favs.text
    assert any(r["id"] == recipe_id for r in member_favs.json())

    owner_favs = await client.get("/api/v1/recipes?favorites_only=true", headers=owner_headers)
    assert owner_favs.status_code == 200, owner_favs.text
    assert all(r["id"] != recipe_id for r in owner_favs.json())


@pytest.mark.asyncio
async def test_cookbook_invitation_token_acceptance(client):
    owner_headers = await _auth_headers(
        client,
        "invite-owner@example.com",
        "invite_owner",
        "SupMeal!InviteOwner#2026",
    )
    invited_headers = await _auth_headers(
        client,
        "invitee@example.com",
        "invitee_user",
        "SupMeal!Invitee#2026",
    )

    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Invite CB", "description": "invite flow"},
        headers=owner_headers,
    )
    assert cb.status_code == 201, cb.text
    cb_id = cb.json()["id"]

    invite = await client.post(
        f"/api/v1/cookbooks/{cb_id}/invitations",
        json={"invited_email": "invitee@example.com", "invited_role": "commentator", "expires_in_days": 7},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    accept = await client.post(
        f"/api/v1/cookbooks/invitations/{token}/accept",
        headers=invited_headers,
    )
    assert accept.status_code == 200, accept.text

    invited_view = await client.get(f"/api/v1/cookbooks/{cb_id}", headers=invited_headers)
    assert invited_view.status_code == 200, invited_view.text
    members = invited_view.json().get("members", [])
    role = next((m["role"] for m in members if m["user"]["username"] == "invitee_user"), None)
    assert role == "commentator"


@pytest.mark.asyncio
async def test_cookbook_invitation_revoke(client):
    owner_headers = await _auth_headers(
        client,
        "invite-revoke-owner@example.com",
        "invite_revoke_owner",
        "SupMeal!InviteRevokeOwner#2026",
    )

    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Invite Revoke", "description": "revoke flow"},
        headers=owner_headers,
    )
    assert cb.status_code == 201, cb.text
    cb_id = cb.json()["id"]

    invite = await client.post(
        f"/api/v1/cookbooks/{cb_id}/invitations",
        json={"invited_email": "revoked@example.com", "invited_role": "reader", "expires_in_days": 7},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    inv_id = invite.json()["id"]

    revoke = await client.delete(
        f"/api/v1/cookbooks/{cb_id}/invitations/{inv_id}",
        headers=owner_headers,
    )
    assert revoke.status_code == 204, revoke.text

    pending = await client.get(
        f"/api/v1/cookbooks/{cb_id}/invitations?only_pending=true",
        headers=owner_headers,
    )
    assert pending.status_code == 200, pending.text
    assert all(i["id"] != inv_id for i in pending.json())


@pytest.mark.asyncio
async def test_cookbook_invitation_expired_returns_400(client, db_session):
    owner_headers = await _auth_headers(
        client,
        "invite-exp-owner@example.com",
        "invite_exp_owner",
        "SupMeal!InviteExpOwner#2026",
    )
    invited_headers = await _auth_headers(
        client,
        "invite-exp-user@example.com",
        "invite_exp_user",
        "SupMeal!InviteExpUser#2026",
    )

    cb = await client.post(
        "/api/v1/cookbooks",
        json={"name": "Invite Exp", "description": "expire flow"},
        headers=owner_headers,
    )
    assert cb.status_code == 201, cb.text
    cb_id = cb.json()["id"]

    invite = await client.post(
        f"/api/v1/cookbooks/{cb_id}/invitations",
        json={"invited_email": "invite-exp-user@example.com", "invited_role": "reader", "expires_in_days": 7},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    result = await db_session.execute(select(CookbookInvitation).where(CookbookInvitation.token == token))
    invitation = result.scalar_one()
    invitation.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    accept = await client.post(
        f"/api/v1/cookbooks/invitations/{token}/accept",
        headers=invited_headers,
    )
    assert accept.status_code == 400, accept.text
    assert "expire" in accept.text.lower()


@pytest.mark.asyncio
async def test_import_json_invalid_schema_returns_422(client):
    headers = await _auth_headers(
        client,
        "invalid-import@example.com",
        "invalid_import_user",
        "SupMeal!InvalidImport#2026",
    )

    payload = {
        "format": "supmeal-json",
        "version": 1,
        "recipes": [
            {
                "title": "Broken",
                "servings": "beaucoup",
                "ingredients": [{"name": "x"}],
                "steps": [{"content": "y"}],
            }
        ],
    }

    upload = await client.post(
        "/api/v1/import-export/json",
        files={
            "file": (
                "invalid.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
        headers=headers,
    )
    assert upload.status_code == 422, upload.text


@pytest.mark.asyncio
async def test_import_csv_invalid_rows_are_reported(client):
    headers = await _auth_headers(
        client,
        "csv-invalid@example.com",
        "csv_invalid_user",
        "SupMeal!CsvInvalid#2026",
    )

    csv_content = "\n".join(
        [
            "title,description,servings,prep_time,cook_time,ingredient,quantity,unit,step,tags,source",
            "Recette OK,desc,2,10,5,tomate,1,pc,melanger,tag,https://example.com",
            "Recette KO,desc,2,10,5,oignon,N/A,pc,cuire,tag,https://example.com",
        ]
    )

    upload = await client.post(
        "/api/v1/import-export/csv",
        files={"file": ("bad.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    data = upload.json()
    assert data["imported_recipes"] == 1
    assert data["ignored_rows"] == 1
    assert len(data["errors"]) == 1
