from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, or_, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Cookbook,
    CookbookPublic,
    Ingredient,
    IngredientPublic,
    Recipe,
    RecipePublic,
    SearchResults,
    User,
    VisibilityEnum,
)

router = APIRouter()


def _search_cookbooks(
    session: Session,
    user: User,
    visibility: VisibilityEnum | None,
    query: str | None,
) -> list[CookbookPublic]:
    """
    Search for cookbooks.

    :param session: Database session
    :param user: Current user
    :param visibility: Optional visibility filter
    :param query: Optional keyword search
    :return: List of matching cookbooks
    """
    cookbook_statement = select(Cookbook).where(Cookbook.owner_id == user.id)

    # Apply visibility filter (if not specified, search all visibilities for user's cookbooks)
    if visibility is not None:
        cookbook_statement = cookbook_statement.where(Cookbook.visibility == visibility)

    # Apply keyword search
    if query:
        cookbook_statement = cookbook_statement.where(
            or_(
                Cookbook.title.ilike(f'%{query}%'),
                Cookbook.description.ilike(f'%{query}%'),
            ),
        )

    return list(session.exec(cookbook_statement).all())


def _search_recipes(
    session: Session,
    user: User,
    tags: list[str] | None,
    query: str | None,
) -> list[RecipePublic]:
    """
    Search for recipes.

    :param session: Database session
    :param user: Current user
    :param tags: Optional list of tags to filter by
    :param query: Optional keyword search
    :return: List of matching recipes
    """
    recipe_statement = select(Recipe).where(Recipe.owner_id == user.id)

    # Apply tags filter
    if tags:
        # Tags are stored as JSON string, so we need to check if any tag matches
        # We check for the tag in the JSON array format: ["tag1", "tag2"]
        tag_conditions = []
        for tag in tags:
            # Escape the tag for JSON string matching
            escaped_tag = tag.replace('"', '\\"')
            # Check if the tag exists in the JSON array stored as string
            tag_conditions.append(Recipe.tags.ilike(f'%"{escaped_tag}"%'))
        if tag_conditions:
            recipe_statement = recipe_statement.where(or_(*tag_conditions))

    # Apply keyword search
    if query:
        recipe_statement = recipe_statement.where(
            or_(
                Recipe.title.ilike(f'%{query}%'),
                Recipe.description.ilike(f'%{query}%'),
            ),
        )

    return list(session.exec(recipe_statement).all())


def _search_ingredients(
    session: Session,
    query: str | None,
) -> list[IngredientPublic]:
    """
    Search for ingredients.

    :param session: Database session
    :param query: Optional keyword search
    :return: List of matching ingredients
    """
    ingredient_statement = select(Ingredient)

    # Apply keyword search
    if query:
        ingredient_statement = ingredient_statement.where(
            or_(
                Ingredient.ingredient.ilike(f'%{query}%'),
                Ingredient.description.ilike(f'%{query}%'),
            ),
        )

    return list(session.exec(ingredient_statement).all())


@router.get('/search', response_model=SearchResults)
def search(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    tags: list[str] | None = Query(None, description='Optional list of tags to filter by'),
    visibility: VisibilityEnum | None = Query(None, description='Optional visibility filter (public or private)'),
    query: str | None = Query(None, description='Optional keyword search'),
    type: list[str] | None = Query(
        None, description='Optional list of types to filter by (cookbook, recipe, ingredient)'
    ),
) -> Any:
    """
    Search for cookbooks, recipes, and ingredients.

    :param tags: Optional list of tags to filter by (applies to recipes)
    :param visibility: Optional visibility filter (applies to cookbooks). Absence implies all.
    :param query: Optional keyword search in titles, descriptions, and ingredient names
    :param type: Optional list of types to filter by ("cookbook", "recipe", "ingredient")
    """
    # Normalize type filter - default to all types if not specified
    search_types = {t.lower() for t in (type or [])} if type else {'cookbook', 'recipe', 'ingredient'}

    results = SearchResults(total_count=0)

    # Search cookbooks
    if 'cookbook' in search_types:
        cookbooks = _search_cookbooks(session, current_user, visibility, query)
        results.cookbooks = cookbooks
        results.total_count += len(cookbooks)

    # Search recipes
    if 'recipe' in search_types:
        recipes = _search_recipes(session, current_user, tags, query)
        results.recipes = recipes
        results.total_count += len(recipes)

    # Search ingredients
    if 'ingredient' in search_types:
        ingredients = _search_ingredients(session, query)
        results.ingredients = ingredients
        results.total_count += len(ingredients)

    return results
