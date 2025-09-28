import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Ingredient, IngredientCreate, IngredientPublic, IngredientsPublic

router = APIRouter()


@router.post('/', response_model=IngredientPublic)
def create_ingredient(*, session: SessionDep, current_user: CurrentUser, item_in: IngredientCreate) -> Any:  # noqa: ARG001
    """
    Create new ingredient.
    """
    ingredient = Ingredient.model_validate(item_in)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


@router.get('/', response_model=IngredientsPublic)
def get_ingredients(*, session: SessionDep, current_user: CurrentUser, offset: int = 0, limit: int = 100) -> Any:  # noqa: ARG001
    """
    Get ingredients.

    :param offset the page offset
    :param limit the limit of ingredients to get
    """
    count_statement = select(func.count()).select_from(Ingredient)
    count = session.exec(count_statement).one()
    statement = select(Ingredient).offset(offset).limit(limit)
    ingredients = session.exec(statement).all()
    return IngredientsPublic(data=ingredients, count=count)


@router.get('/{ingredient_id}', response_model=IngredientPublic)
def get_ingredient(ingredient_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:  # noqa: ARG001
    """
    Get ingredient by id.
    """
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail='The ingredient was not found',
        )
    return ingredient
