import pytest

from app.api.v1.endpoints import _oauth_codes
from app.core.security import create_access_token


async def _register(
    client,
    email: str,
    username: str,
    password: str = "SupMeal!Quality2026",
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


@pytest.mark.asyncio
async def test_auth_and_user_profile_error_paths(client):
    weak = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "username": "weak_user",
            "password": "abcdefgh",
        },
    )
    assert weak.status_code == 422

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "SupMeal!Quality2026",
        },
    )
    assert bad_login.status_code == 401

    headers, body = await _register(
        client,
        "quality-user@example.com",
        "quality_user",
    )

    user_id = body["user"]["id"]

    me = await client.get(
        "/api/v1/auth/me",
        headers=headers,
    )
    assert me.status_code == 200
    assert me.json()["id"] == user_id

    csrf = await client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200
    assert csrf.json()["csrf_token"]

    users = await client.get(
        "/api/v1/users?q=quality",
        headers=headers,
    )
    assert users.status_code == 200
    assert any(u["id"] == user_id for u in users.json())

    fetched = await client.get(
        f"/api/v1/users/{user_id}",
        headers=headers,
    )
    assert fetched.status_code == 200

    missing = await client.get(
        "/api/v1/users/999999",
        headers=headers,
    )
    assert missing.status_code == 404

    updated = await client.patch(
        "/api/v1/users/me",
        json={
            "full_name": "Quality User",
            "dietary_preferences": "vegetarian",
            "allergies": "nuts",
            "favorite_cuisines": "guinean,french",
            "default_servings": 6,
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Quality User"
    assert updated.json()["default_servings"] == 6

    wrong_password = await client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "WrongPassword1!",
            "new_password": "NewPassword2!",
        },
        headers=headers,
    )
    assert wrong_password.status_code == 400

    changed = await client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "SupMeal!Quality2026",
            "new_password": "NewPassword2!",
        },
        headers=headers,
    )
    assert changed.status_code == 204, changed.text

    old_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "quality-user@example.com",
            "password": "SupMeal!Quality2026",
        },
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "quality-user@example.com",
            "password": "NewPassword2!",
        },
    )
    assert new_login.status_code == 200

    bad_type = await client.post(
        "/api/v1/users/me/avatar",
        files={
            "file": (
                "avatar.txt",
                b"hello",
                "text/plain",
            )
        },
        headers=headers,
    )
    assert bad_type.status_code == 400

    bad_content = await client.post(
        "/api/v1/users/me/avatar",
        files={
            "file": (
                "avatar.png",
                b"not-a-real-png",
                "image/png",
            )
        },
        headers=headers,
    )
    assert bad_content.status_code == 400

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204


@pytest.mark.asyncio
async def test_oauth_exchange_endpoint_paths(client):
    _oauth_codes._codes.clear()

    missing = await client.post(
        "/api/v1/auth/exchange",
        json={"code": ""},
    )
    assert missing.status_code == 400

    _oauth_codes.store_code(
        "bad-token-code",
        "this-is-not-a-jwt",
    )

    invalid_token = await client.post(
        "/api/v1/auth/exchange",
        json={"code": "bad-token-code"},
    )
    assert invalid_token.status_code == 400

    _, body = await _register(
        client,
        "exchange@example.com",
        "exchange_user",
    )

    token = body["access_token"]

    _oauth_codes.store_code(
        "valid-code",
        token,
    )

    exchanged = await client.post(
        "/api/v1/auth/exchange",
        json={"code": "valid-code"},
    )
    assert exchanged.status_code == 200, exchanged.text
    assert exchanged.json()["user"]["id"] == body["user"]["id"]

    replay = await client.post(
        "/api/v1/auth/exchange",
        json={"code": "valid-code"},
    )
    assert replay.status_code == 400

    ghost_token = create_access_token(999999)

    _oauth_codes.store_code(
        "ghost-code",
        ghost_token,
    )

    ghost = await client.post(
        "/api/v1/auth/exchange",
        json={"code": "ghost-code"},
    )
    assert ghost.status_code == 401


@pytest.mark.asyncio
async def test_personal_meal_plan_validation_and_lifecycle(client):
    headers, _ = await _register(
        client,
        "meal-quality@example.com",
        "meal_quality",
    )

    recipe = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Meal quality recipe",
            "ingredients": [
                {
                    "name": "rice",
                    "quantity": 1,
                    "unit": "kg",
                    "position": 0,
                }
            ],
            "steps": [
                {
                    "content": "Cook rice",
                    "position": 0,
                }
            ],
        },
        headers=headers,
    )
    assert recipe.status_code == 201, recipe.text

    recipe_id = recipe.json()["id"]

    invalid_slot = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "planned_date": "2026-08-20",
            "meal_slot": "brunch",
            "servings": 4,
        },
        headers=headers,
    )
    assert invalid_slot.status_code == 400

    invalid_date = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "planned_date": "20/08/2026",
            "meal_slot": "lunch",
            "servings": 4,
        },
        headers=headers,
    )
    assert invalid_date.status_code == 400

    missing_recipe = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": 999999,
            "planned_date": "2026-08-20",
            "meal_slot": "lunch",
            "servings": 4,
        },
        headers=headers,
    )
    assert missing_recipe.status_code == 404

    created = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "planned_date": "2026-08-20",
            "meal_slot": "lunch",
            "servings": 4,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    plan_id = created.json()["id"]

    duplicate = await client.post(
        "/api/v1/meal-plans",
        json={
            "recipe_id": recipe_id,
            "planned_date": "2026-08-20",
            "meal_slot": "lunch",
            "servings": 2,
        },
        headers=headers,
    )
    assert duplicate.status_code == 409

    listed = await client.get(
        (
            "/api/v1/meal-plans"
            "?start_date=2026-08-01"
            "&end_date=2026-08-31"
        ),
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(p["id"] == plan_id for p in listed.json())

    missing_delete = await client.delete(
        "/api/v1/meal-plans/999999",
        headers=headers,
    )
    assert missing_delete.status_code == 404

    deleted = await client.delete(
        f"/api/v1/meal-plans/{plan_id}",
        headers=headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_cookbook_full_management_and_invitations(client):
    owner_headers, owner = await _register(
        client,
        "cb-owner-quality@example.com",
        "cb_owner_quality",
    )

    member_headers, member = await _register(
        client,
        "cb-member-quality@example.com",
        "cb_member_quality",
    )

    invited_headers, invited = await _register(
        client,
        "cb-invited-quality@example.com",
        "cb_invited_quality",
    )

    created = await client.post(
        "/api/v1/cookbooks",
        json={
            "name": "Quality Cookbook",
            "description": "Coverage cookbook",
        },
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text

    cookbook_id = created.json()["id"]

    listed = await client.get(
        "/api/v1/cookbooks",
        headers=owner_headers,
    )
    assert listed.status_code == 200
    assert any(c["id"] == cookbook_id for c in listed.json())

    detail = await client.get(
        f"/api/v1/cookbooks/{cookbook_id}",
        headers=owner_headers,
    )
    assert detail.status_code == 200

    updated = await client.patch(
        f"/api/v1/cookbooks/{cookbook_id}",
        json={
            "name": "Quality Cookbook Updated",
            "description": "Updated description",
        },
        headers=owner_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Quality Cookbook Updated"

    unknown_member = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/members",
        json={
            "user_email": "nobody@example.com",
            "role": "reader",
        },
        headers=owner_headers,
    )
    assert unknown_member.status_code == 404

    added = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/members",
        json={
            "user_email": "cb-member-quality@example.com",
            "role": "reader",
        },
        headers=owner_headers,
    )
    assert added.status_code == 201

    duplicate = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/members",
        json={
            "user_email": "cb-member-quality@example.com",
            "role": "reader",
        },
        headers=owner_headers,
    )
    assert duplicate.status_code == 409

    own_role = await client.patch(
        (
            f"/api/v1/cookbooks/{cookbook_id}"
            f"/members/{owner['user']['id']}"
        ),
        json={"role": "editor"},
        headers=owner_headers,
    )
    assert own_role.status_code == 400

    promoted = await client.patch(
        (
            f"/api/v1/cookbooks/{cookbook_id}"
            f"/members/{member['user']['id']}"
        ),
        json={"role": "editor"},
        headers=owner_headers,
    )
    assert promoted.status_code == 204

    forbidden_update = await client.patch(
        f"/api/v1/cookbooks/{cookbook_id}",
        json={"description": "member edit"},
        headers=member_headers,
    )
    assert forbidden_update.status_code == 403

    left = await client.delete(
        (
            f"/api/v1/cookbooks/{cookbook_id}"
            f"/members/{member['user']['id']}"
        ),
        headers=member_headers,
    )
    assert left.status_code == 204

    invitation = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/invitations",
        json={
            "invited_email": "cb-invited-quality@example.com",
            "invited_role": "reader",
            "expires_in_days": 7,
        },
        headers=owner_headers,
    )
    assert invitation.status_code == 201, invitation.text

    invitation_body = invitation.json()
    invitation_token = invitation_body["token"]

    invitations = await client.get(
        f"/api/v1/cookbooks/{cookbook_id}/invitations",
        headers=owner_headers,
    )
    assert invitations.status_code == 200
    assert any(
        i["id"] == invitation_body["id"]
        for i in invitations.json()
    )

    wrong_recipient = await client.post(
        f"/api/v1/cookbooks/invitations/{invitation_token}/accept",
        headers=member_headers,
    )
    assert wrong_recipient.status_code == 403

    accepted = await client.post(
        f"/api/v1/cookbooks/invitations/{invitation_token}/accept",
        headers=invited_headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["cookbook_id"] == cookbook_id

    replay = await client.post(
        f"/api/v1/cookbooks/invitations/{invitation_token}/accept",
        headers=invited_headers,
    )
    assert replay.status_code == 400

    cookbook_recipe = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/recipes",
        json={
            "title": "Curry poulet quality",
            "prep_time_minutes": 10,
            "cook_time_minutes": 20,
            "ingredients": [
                {
                    "name": "poulet",
                    "quantity": 1,
                    "unit": "kg",
                    "position": 0,
                },
                {
                    "name": "curry",
                    "quantity": 2,
                    "unit": "tbsp",
                    "position": 1,
                },
            ],
            "steps": [
                {
                    "content": "Cuire le poulet",
                    "position": 0,
                }
            ],
        },
        headers=owner_headers,
    )
    assert cookbook_recipe.status_code == 201, cookbook_recipe.text

    recipe_id = cookbook_recipe.json()["id"]

    filtered_recipes = await client.get(
        (
            f"/api/v1/cookbooks/{cookbook_id}/recipes"
            "?search=Curry"
            "&ingredient=poulet"
            "&max_prep_time=15"
        ),
        headers=owner_headers,
    )
    assert filtered_recipes.status_code == 200
    assert any(r["id"] == recipe_id for r in filtered_recipes.json())

    favorite = await client.post(
        f"/api/v1/recipes/{recipe_id}/favorite",
        headers=owner_headers,
    )
    assert favorite.status_code == 200

    favorites = await client.get(
        (
            f"/api/v1/cookbooks/{cookbook_id}/recipes"
            "?favorites_only=true"
        ),
        headers=owner_headers,
    )
    assert favorites.status_code == 200
    assert any(r["id"] == recipe_id for r in favorites.json())

    message = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/messages",
        json={"content": "Message de couverture"},
        headers=invited_headers,
    )
    assert message.status_code == 201

    message_id = message.json()["id"]

    history = await client.get(
        (
            f"/api/v1/cookbooks/{cookbook_id}/messages"
            f"?before_id={message_id + 1}"
        ),
        headers=invited_headers,
    )
    assert history.status_code == 200
    assert any(m["id"] == message_id for m in history.json())

    invitation_two = await client.post(
        f"/api/v1/cookbooks/{cookbook_id}/invitations",
        json={
            "invited_email": "later-quality@example.com",
            "invited_role": "editor",
            "expires_in_days": 3,
        },
        headers=owner_headers,
    )
    assert invitation_two.status_code == 201

    revoked = await client.delete(
        (
            f"/api/v1/cookbooks/{cookbook_id}/invitations/"
            f"{invitation_two.json()['id']}"
        ),
        headers=owner_headers,
    )
    assert revoked.status_code == 204

    all_invitations = await client.get(
        (
            f"/api/v1/cookbooks/{cookbook_id}/invitations"
            "?only_pending=false"
        ),
        headers=owner_headers,
    )
    assert all_invitations.status_code == 200
    assert len(all_invitations.json()) >= 2

    forbidden_delete = await client.delete(
        f"/api/v1/cookbooks/{cookbook_id}",
        headers=invited_headers,
    )
    assert forbidden_delete.status_code == 403

    deleted = await client.delete(
        f"/api/v1/cookbooks/{cookbook_id}",
        headers=owner_headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_recipe_update_filters_favorite_comments_and_delete(client):
    owner_headers, _ = await _register(
        client,
        "recipe-owner-quality@example.com",
        "recipe_owner_quality",
    )

    outsider_headers, _ = await _register(
        client,
        "recipe-outsider-quality@example.com",
        "recipe_outsider_quality",
    )

    created = await client.post(
        "/api/v1/recipes",
        json={
            "title": "Private quality recipe",
            "description": "Initial",
            "prep_time_minutes": 15,
            "cook_time_minutes": 25,
            "is_public": False,
            "ingredients": [
                {
                    "name": "tomate",
                    "quantity": 2,
                    "unit": "piece",
                    "position": 0,
                }
            ],
            "steps": [
                {
                    "content": "Couper tomate",
                    "position": 0,
                }
            ],
        },
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text

    recipe_id = created.json()["id"]

    forbidden_read = await client.get(
        f"/api/v1/recipes/{recipe_id}",
        headers=outsider_headers,
    )
    assert forbidden_read.status_code == 403

    updated = await client.patch(
        f"/api/v1/recipes/{recipe_id}",
        json={
            "title": "Recette Qualite Tomate",
            "description": "Updated",
            "prep_time_minutes": 12,
            "cook_time_minutes": 20,
            "ingredients": [
                {
                    "name": "tomate rouge",
                    "quantity": 3,
                    "unit": "piece",
                    "position": 0,
                },
                {
                    "name": "oignon",
                    "quantity": 1,
                    "unit": "piece",
                    "position": 1,
                },
            ],
            "steps": [
                {
                    "content": "Couper les legumes",
                    "position": 0,
                },
                {
                    "content": "Cuire doucement",
                    "position": 1,
                },
            ],
        },
        headers=owner_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Recette Qualite Tomate"
    assert len(updated.json()["ingredients"]) == 2

    filtered = await client.get(
        (
            "/api/v1/recipes"
            "?ingredient=tomate"
            "&max_prep_time=15"
            "&max_cook_time=25"
            "&search=Qualite"
        ),
        headers=owner_headers,
    )
    assert filtered.status_code == 200
    assert any(r["id"] == recipe_id for r in filtered.json())

    favorite_on = await client.post(
        f"/api/v1/recipes/{recipe_id}/favorite",
        headers=owner_headers,
    )
    assert favorite_on.status_code == 200
    assert favorite_on.json()["is_favorite"] is True

    favorite_off = await client.post(
        f"/api/v1/recipes/{recipe_id}/favorite",
        headers=owner_headers,
    )
    assert favorite_off.status_code == 200
    assert favorite_off.json()["is_favorite"] is False

    bad_image_type = await client.post(
        f"/api/v1/recipes/{recipe_id}/image",
        files={
            "file": (
                "recipe.txt",
                b"hello",
                "text/plain",
            )
        },
        headers=owner_headers,
    )
    assert bad_image_type.status_code == 400

    bad_image_content = await client.post(
        f"/api/v1/recipes/{recipe_id}/image",
        files={
            "file": (
                "recipe.png",
                b"not-a-real-png",
                "image/png",
            )
        },
        headers=owner_headers,
    )
    assert bad_image_content.status_code == 400

    comment = await client.post(
        f"/api/v1/recipes/{recipe_id}/comments",
        json={"content": "Commentaire quality"},
        headers=owner_headers,
    )
    assert comment.status_code == 201

    comment_id = comment.json()["id"]

    comments = await client.get(
        f"/api/v1/recipes/{recipe_id}/comments",
        headers=owner_headers,
    )
    assert comments.status_code == 200
    assert any(c["id"] == comment_id for c in comments.json())

    deleted_comment = await client.delete(
        f"/api/v1/recipes/{recipe_id}/comments/{comment_id}",
        headers=owner_headers,
    )
    assert deleted_comment.status_code == 204

    forbidden_delete = await client.delete(
        f"/api/v1/recipes/{recipe_id}",
        headers=outsider_headers,
    )
    assert forbidden_delete.status_code == 403

    deleted = await client.delete(
        f"/api/v1/recipes/{recipe_id}",
        headers=owner_headers,
    )
    assert deleted.status_code == 204

    missing = await client.get(
        f"/api/v1/recipes/{recipe_id}",
        headers=owner_headers,
    )
    assert missing.status_code == 404
