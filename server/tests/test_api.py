"""Tests d'integration : auth, recettes, cookbooks."""

import pytest


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

    # Guest cannot post message
    r = await client.post(
        f"/api/v1/cookbooks/{cb_id}/messages",
        json={"content": "Hello"},
        headers=guest_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_import_export_json(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "ex@example.com", "username": "ex", "password": "Motdepasse1"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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