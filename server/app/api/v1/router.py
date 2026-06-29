"""Router principal v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    cookbooks,
    import_export,
    meal_plans,
    oauth,
    recipes,
    shopping,
    tags,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(cookbooks.router, prefix="/cookbooks", tags=["cookbooks"])
api_router.include_router(meal_plans.router, prefix="/meal-plans", tags=["meal-plans"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(shopping.router, prefix="/shopping", tags=["shopping"])
api_router.include_router(import_export.router, prefix="/import-export", tags=["import-export"])