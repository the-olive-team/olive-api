import base64
import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.s3 import get_file_extension, s3_service
from app.models import (
    Cookbook,
    Ingredient,
    Recipe,
    RecipeCreate,
    RecipeIngredient,
    RecipePublic,
    RecipeStep,
    RecipeUpdate,
)

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


@router.put('/{recipe_uuid}', response_model=RecipePublic)
async def update_recipe(
    recipe_uuid: uuid.UUID,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_in: RecipeUpdate,
) -> Any:
    """
    Update recipe by id.
    """
    recipe = session.get(Recipe, recipe_uuid)
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

    # Validate cookbook exists
    cookbook = session.get(Cookbook, item_in.cookbook_uuid)
    if not cookbook:
        raise HTTPException(
            status_code=400,
            detail='The cookbook does not exist',
        )

    # Validate cloned_from recipe exists if provided
    if item_in.cloned_from:
        cloned_recipe = session.get(Recipe, item_in.cloned_from)
        if not cloned_recipe:
            raise HTTPException(
                status_code=400,
                detail='The cloned_from recipe does not exist',
            )

    # Update recipe fields
    recipe.title = item_in.title
    recipe.description = item_in.description
    recipe.cookbook_id = item_in.cookbook_uuid
    recipe.cloned_from = item_in.cloned_from
    recipe.tags = json.dumps(item_in.tags) if item_in.tags else None

    # Delete existing recipe ingredients and steps
    existing_ingredients = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_uuid),
    ).all()
    for ingredient in existing_ingredients:
        session.delete(ingredient)

    existing_steps = session.exec(select(RecipeStep).where(RecipeStep.recipe_id == recipe_uuid)).all()
    # Delete old step pictures from S3
    for step in existing_steps:
        if step.step_picture:
            s3_service.delete_file(step.step_picture)
        session.delete(step)

    session.commit()

    # Create new recipe ingredients
    for idx, ingredient_data in enumerate(item_in.recipe_ingredients):
        # Validate ingredient exists
        ingredient = session.get(Ingredient, ingredient_data.ingredient_id)
        if not ingredient:
            raise HTTPException(
                status_code=400,
                detail=f'Ingredient with id {ingredient_data.ingredient_id} does not exist',
            )

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe_uuid,
            ingredient_id=ingredient_data.ingredient_id,
            quantity=ingredient_data.quantity,
            unit=ingredient_data.unit,
            comments=ingredient_data.comments,
            order_number=idx,
        )
        session.add(recipe_ingredient)

    # Create new recipe steps
    for idx, step_data in enumerate(item_in.recipe_steps):
        step_picture_key = None
        if step_data.step_picture:
            try:
                # Decode base64 image
                if step_data.step_picture.startswith('data:image/'):
                    # Handle data URL format: data:image/jpeg;base64,...
                    header, encoded = step_data.step_picture.split(',', 1)
                    content_type = header.split(';')[0].split(':')[1]
                else:
                    # Assume it's just base64 encoded
                    encoded = step_data.step_picture
                    content_type = 'image/jpeg'

                image_bytes = base64.b64decode(encoded)

                # Validate file size (10MB max)
                MAX_FILE_SIZE = 10 * 1024 * 1024
                if len(image_bytes) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail='Step picture size exceeds maximum allowed size (10MB)',
                    )

                # Generate S3 key and upload
                extension = get_file_extension(content_type.split('/')[1] if '/' in content_type else 'jpg')
                unique_id = uuid.uuid4()
                step_picture_key = f'recipes/{recipe_uuid}/step-{idx}-{unique_id}.{extension}'
                s3_service.upload_file(image_bytes, step_picture_key, content_type=content_type)
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f'Failed to process step picture: {str(e)}',
                )

        recipe_step = RecipeStep(
            recipe_id=recipe_uuid,
            step_instructions=step_data.step_instructions,
            step_picture=step_picture_key,
            order_number=idx,
        )
        session.add(recipe_step)

    session.add(recipe)
    session.commit()
    session.refresh(recipe)
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
