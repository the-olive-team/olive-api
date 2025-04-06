from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes import cookbooks, ingredients, login, users, utils

api_router = APIRouter()
api_router.include_router(login.router, tags=['login'])
api_router.include_router(users.router, prefix='/users', tags=['users'])
api_router.include_router(utils.router, prefix='/utils', tags=['utils'])
api_router.include_router(cookbooks.router, prefix='/cookbooks', tags=['cookbooks'])
api_router.include_router(
    ingredients.router,
    prefix='/ingredients',
    tags=['ingredients'],
    dependencies=[Depends(get_current_user)],
)
