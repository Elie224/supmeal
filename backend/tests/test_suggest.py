"""Tests pour le suggester de recettes par ingredients."""

from __future__ import annotations

import pytest


async def _register_and_token(client, email: str, username: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": "Motdepasse1"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["access_token"]


async def _create_recipe(
    client,
    headers: dict[str, str],
    *,
    title: str,
    ingredients: list[str],
    is_public: bool = False,
    cookbook_id: int | None = None,
    prep: int = 10,
    cook: int = 20,
) -> int:
    payload: dict = {
        "title": title,
        "servings": 4,
        "prep_time_minutes": prep,
        "cook_time_minutes": cook,
        "is_public": is_public,
        "ingredients": [{"name": i, "position": idx} for idx, i in enumerate(ingredients)],
        "steps": [{"content": "Mixer.", "position": 0}],
    }
    if cookbook_id is not None:
        payload["cookbook_id"] = cookbook_id
    r = await client.post("/api/v1/recipes", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_suggest_returns_recipes_with_match_score(client):
    token = await _register_and_token(client, "chef1@example.com", "chef1")
    headers = {"Authorization": f"Bearer {token}"}
    await _create_recipe(
        client,
        headers,
        title="Tomates farcies",
        ingredients=["tomate", "viande hachee", "oignon", "ail"],
    )
    await _create_recipe(
        client,
        headers,
        title="Pates carbonara",
        ingredients=["pates", "creme", "lardons", "oeuf", "parmesan"],
    )

    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["tomate", "oignon", "ail"]},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert first["recipe"]["title"] == "Tomates farcies"
    assert first["match_score"] >= 0.99
    assert set(first["matched_ingredients"]) == {"tomate", "oignon", "ail"}
    assert "viande hachee" in first["missing_ingredients"]


@pytest.mark.asyncio
async def test_suggest_respects_visibility(client):
    token_a = await _register_and_token(client, "owner@example.com", "owner")
    token_b = await _register_and_token(client, "intruder@example.com", "intruder")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    # Recette PERSO de A : B ne doit pas la voir
    await _create_recipe(
        client,
        headers_a,
        title="Gateau secret",
        ingredients=["chocolat", "beurre", "farine"],
    )
    # Recette publique de A : B doit la voir
    await _create_recipe(
        client,
        headers_a,
        title="Salade Cesar publique",
        ingredients=["salade", "poulet", "parmesan"],
        is_public=True,
    )
    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["chocolat", "farine"]},
        headers=headers_b,
    )
    assert r.status_code == 200, r.text
    titles = [s["recipe"]["title"] for s in r.json()]
    assert "Gateau secret" not in titles  # prive, pas visible
    assert "Salade Cesar publique" not in titles  # pas d ingredient matchant


@pytest.mark.asyncio
async def test_suggest_filters_by_max_prep_time(client):
    token = await _register_and_token(client, "fast@example.com", "fast")
    headers = {"Authorization": f"Bearer {token}"}
    await _create_recipe(
        client,
        headers,
        title="Express",
        ingredients=["pates", "beurre"],
        prep=5,
        cook=5,
    )
    await _create_recipe(
        client,
        headers,
        title="Long",
        ingredients=["pates", "sauce"],
        prep=120,
        cook=120,
    )
    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["pates"], "max_prep_time": 15},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    titles = [s["recipe"]["title"] for s in r.json()]
    assert titles == ["Express"]


@pytest.mark.asyncio
async def test_suggest_accent_insensitive(client):
    token = await _register_and_token(client, "accent@example.com", "accent")
    headers = {"Authorization": f"Bearer {token}"}
    await _create_recipe(
        client,
        headers,
        title="Recette francaise",
        ingredients=["échalote", "crème fraîche", "beurre"],
    )
    # L utilisateur saisit sans accents et avec espaces differents
    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["echalote", "CREME  fraiCHE", "beurre"]},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    assert data[0]["match_score"] >= 0.99


@pytest.mark.asyncio
async def test_suggest_empty_ingredients_returns_empty(client):
    token = await _register_and_token(client, "empty@example.com", "empty")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["", "  ", ""]},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_suggest_unauthenticated_sees_only_public(client):
    token = await _register_and_token(client, "pub@example.com", "pub")
    headers = {"Authorization": f"Bearer {token}"}
    await _create_recipe(
        client,
        headers,
        title="Publique",
        ingredients=["tomate", "sel"],
        is_public=True,
    )
    await _create_recipe(
        client,
        headers,
        title="Privee",
        ingredients=["tomate", "sucre"],
        is_public=False,
    )
    r = await client.post(
        "/api/v1/recipes/suggest",
        json={"ingredients": ["tomate"]},
    )
    assert r.status_code == 200, r.text
    titles = [s["recipe"]["title"] for s in r.json()]
    assert "Publique" in titles
    assert "Privee" not in titles
