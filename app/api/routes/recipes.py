import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models import Cookbook, Recipe, RecipeCreate, RecipePublic

router = APIRouter()


@router.post('/', response_model=RecipePublic)
def create_recipe(*, session: SessionDep, current_user: CurrentUser, item_in: RecipeCreate) -> Any:
    """
    Create new recipe.
    """
    cookbook = session.get(Cookbook, item_in.cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=400,
            detail='The cookbook does not exist',
        )
    recipe = Recipe.model_validate(item_in, update={'owner_id': current_user.id})
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@router.get('/{recipe_id}', response_model=RecipePublic)
def get_recipe(recipe_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get recipe by id.
    """
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=404,
            detail='The recipe was not found',
        )
    if recipe.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return recipe


@router.delete('/{recipe_id}', response_model=RecipePublic)
def delete_recipe(recipe_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete recipe by id.
    """
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=404,
            detail='The recipe was not found',
        )
    if recipe.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    session.delete(recipe)
    session.commit()
    return recipe
