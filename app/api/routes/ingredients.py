import base64
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException

from app.api.deps import SessionDep
from app.models import Ingredient, IngredientCreate

router = APIRouter()


@router.get('/{ingredient_id}')
def get_ingredient(cookbook_id: uuid.UUID, session: SessionDep) -> Ingredient:
    """
    Get ingredient by id.
    """
    if not (ingredient := session.get(Ingredient, cookbook_id)):
        raise HTTPException(
            status_code=404,
            detail='Ingredient was not found',
        )
    return ingredient


@router.get('/{ingredient_id}')
def create_ingredient(data: Annotated[IngredientCreate, Form()], session: SessionDep) -> Ingredient:
    """
    Add a new ingredient.
    """
    resource_path = base64.b64encode(os.path.basename(data.image))
    ingredient = Ingredient.model_validate(data, update={'image': resource_path})
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient
