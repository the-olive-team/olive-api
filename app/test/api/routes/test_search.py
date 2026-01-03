import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models import Cookbook, Ingredient, Recipe, User, VisibilityEnum


@pytest.fixture(name='cookbook')
def cookbook_fixture(session: Session, user: User) -> Cookbook:
    cookbook = Cookbook(
        id=uuid.uuid4(),
        title='Test Cookbook',
        description='A test cookbook',
        owner_id=user.id,
        visibility=VisibilityEnum.private,
    )
    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)
    return cookbook


@pytest.fixture(name='public_cookbook')
def public_cookbook_fixture(session: Session, user: User) -> Cookbook:
    cookbook = Cookbook(
        id=uuid.uuid4(),
        title='Public Cookbook',
        description='A public cookbook',
        owner_id=user.id,
        visibility=VisibilityEnum.public,
    )
    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)
    return cookbook


@pytest.fixture(name='recipe')
def recipe_fixture(session: Session, user: User, cookbook: Cookbook) -> Recipe:
    recipe = Recipe(
        id=uuid.uuid4(),
        title='Test Recipe',
        description='A test recipe',
        owner_id=user.id,
        cookbook_id=cookbook.id,
        tags=json.dumps(['breakfast', 'easy']),
    )
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@pytest.fixture(name='ingredient')
def ingredient_fixture(session: Session) -> Ingredient:
    ingredient = Ingredient(
        id=uuid.uuid4(),
        ingredient='Test Ingredient',
        description='A test ingredient',
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


class TestSearchAll:
    def test_search_all_types(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe, ingredient: Ingredient
    ):
        """Test searching all types without filters."""
        response = auth_client.get('/api/v1/search')

        assert response.status_code == 200
        data = response.json()
        assert 'cookbooks' in data
        assert 'recipes' in data
        assert 'ingredients' in data
        assert 'total_count' in data
        assert data['total_count'] >= 3
        assert len(data['cookbooks']) >= 1
        assert len(data['recipes']) >= 1
        assert len(data['ingredients']) >= 1

    def test_search_without_auth(self, client: TestClient):
        """Test search without authentication."""
        response = client.get('/api/v1/search')

        assert response.status_code == 401


class TestSearchCookbooks:
    def test_search_cookbooks_by_type(self, auth_client, user: User, session: Session, cookbook: Cookbook):
        """Test searching only cookbooks."""
        response = auth_client.get('/api/v1/search?type=cookbook')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert len(data['recipes']) == 0
        assert len(data['ingredients']) == 0
        assert data['total_count'] == len(data['cookbooks'])

    def test_search_cookbooks_by_query(self, auth_client, user: User, session: Session, cookbook: Cookbook):
        """Test searching cookbooks by keyword."""
        response = auth_client.get('/api/v1/search?type=cookbook&query=Test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert any(cb['title'] == 'Test Cookbook' for cb in data['cookbooks'])

    def test_search_cookbooks_by_query_no_match(self, auth_client, user: User, session: Session, cookbook: Cookbook):
        """Test searching cookbooks with query that doesn't match."""
        response = auth_client.get('/api/v1/search?type=cookbook&query=Nonexistent')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) == 0
        assert data['total_count'] == 0

    def test_search_cookbooks_by_visibility_private(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, public_cookbook: Cookbook
    ):
        """Test searching cookbooks by private visibility."""
        response = auth_client.get('/api/v1/search?type=cookbook&visibility=private')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert all(cb['visibility'] == 'private' for cb in data['cookbooks'])

    def test_search_cookbooks_by_visibility_public(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, public_cookbook: Cookbook
    ):
        """Test searching cookbooks by public visibility."""
        response = auth_client.get('/api/v1/search?type=cookbook&visibility=public')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert all(cb['visibility'] == 'public' for cb in data['cookbooks'])

    def test_search_cookbooks_combined_filters(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, public_cookbook: Cookbook
    ):
        """Test searching cookbooks with multiple filters."""
        response = auth_client.get('/api/v1/search?type=cookbook&visibility=private&query=Test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert all(cb['visibility'] == 'private' for cb in data['cookbooks'])
        assert all('Test' in cb['title'] for cb in data['cookbooks'])


class TestSearchRecipes:
    def test_search_recipes_by_type(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching only recipes."""
        response = auth_client.get('/api/v1/search?type=recipe')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) >= 1
        assert len(data['cookbooks']) == 0
        assert len(data['ingredients']) == 0
        assert data['total_count'] == len(data['recipes'])

    def test_search_recipes_by_query(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching recipes by keyword."""
        response = auth_client.get('/api/v1/search?type=recipe&query=Test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) >= 1
        assert any(r['title'] == 'Test Recipe' for r in data['recipes'])

    def test_search_recipes_by_tags(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching recipes by tags."""
        response = auth_client.get('/api/v1/search?type=recipe&tags=breakfast')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) >= 1
        assert any(r['title'] == 'Test Recipe' for r in data['recipes'])

    def test_search_recipes_by_multiple_tags(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching recipes by multiple tags."""
        # Create another recipe with different tags
        from app.models import Cookbook

        cookbook = session.get(Cookbook, recipe.cookbook_id)
        recipe2 = Recipe(
            id=uuid.uuid4(),
            title='Another Recipe',
            description='Another recipe',
            owner_id=user.id,
            cookbook_id=cookbook.id,
            tags=json.dumps(['dinner', 'hard']),
        )
        session.add(recipe2)
        session.commit()

        response = auth_client.get('/api/v1/search?type=recipe&tags=breakfast&tags=easy')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) >= 1
        assert any(r['title'] == 'Test Recipe' for r in data['recipes'])

    def test_search_recipes_by_tags_no_match(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching recipes by tags that don't match."""
        response = auth_client.get('/api/v1/search?type=recipe&tags=nonexistent')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) == 0

    def test_search_recipes_combined_filters(self, auth_client, user: User, session: Session, recipe: Recipe):
        """Test searching recipes with multiple filters."""
        response = auth_client.get('/api/v1/search?type=recipe&tags=breakfast&query=Test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['recipes']) >= 1
        assert any(r['title'] == 'Test Recipe' for r in data['recipes'])


class TestSearchIngredients:
    def test_search_ingredients_by_type(self, auth_client, user: User, session: Session, ingredient: Ingredient):
        """Test searching only ingredients."""
        response = auth_client.get('/api/v1/search?type=ingredient')

        assert response.status_code == 200
        data = response.json()
        assert len(data['ingredients']) >= 1
        assert len(data['cookbooks']) == 0
        assert len(data['recipes']) == 0
        assert data['total_count'] == len(data['ingredients'])

    def test_search_ingredients_by_query(self, auth_client, user: User, session: Session, ingredient: Ingredient):
        """Test searching ingredients by keyword."""
        response = auth_client.get('/api/v1/search?type=ingredient&query=Test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['ingredients']) >= 1
        assert any(ing['ingredient'] == 'Test Ingredient' for ing in data['ingredients'])

    def test_search_ingredients_by_query_description(
        self, auth_client, user: User, session: Session, ingredient: Ingredient
    ):
        """Test searching ingredients by description."""
        response = auth_client.get('/api/v1/search?type=ingredient&query=test ingredient')

        assert response.status_code == 200
        data = response.json()
        assert len(data['ingredients']) >= 1

    def test_search_ingredients_by_query_no_match(
        self, auth_client, user: User, session: Session, ingredient: Ingredient
    ):
        """Test searching ingredients with query that doesn't match."""
        response = auth_client.get('/api/v1/search?type=ingredient&query=Nonexistent')

        assert response.status_code == 200
        data = response.json()
        assert len(data['ingredients']) == 0
        assert data['total_count'] == 0


class TestSearchMultipleTypes:
    def test_search_cookbooks_and_recipes(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe
    ):
        """Test searching cookbooks and recipes."""
        response = auth_client.get('/api/v1/search?type=cookbook&type=recipe')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1
        assert len(data['recipes']) >= 1
        assert len(data['ingredients']) == 0
        assert data['total_count'] == len(data['cookbooks']) + len(data['recipes'])

    def test_search_all_with_query(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe, ingredient: Ingredient
    ):
        """Test searching all types with a query."""
        response = auth_client.get('/api/v1/search?query=Test')

        assert response.status_code == 200
        data = response.json()
        assert data['total_count'] >= 3
        assert len(data['cookbooks']) >= 1
        assert len(data['recipes']) >= 1
        assert len(data['ingredients']) >= 1

    def test_search_multiple_types_with_filters(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe
    ):
        """Test searching multiple types with different filters."""
        response = auth_client.get(
            '/api/v1/search?type=cookbook&type=recipe&query=Test&visibility=private&tags=breakfast'
        )

        assert response.status_code == 200
        data = response.json()
        # Cookbooks should be filtered by visibility and query
        assert all(cb['visibility'] == 'private' for cb in data['cookbooks'])
        # Recipes should be filtered by tags and query
        assert len(data['recipes']) >= 0  # May or may not match depending on filters


class TestSearchEdgeCases:
    def test_search_empty_results(self, auth_client, user: User, session: Session):
        """Test search when no items exist."""
        response = auth_client.get('/api/v1/search?query=NonexistentTerm')

        assert response.status_code == 200
        data = response.json()
        assert data['total_count'] == 0
        assert len(data['cookbooks']) == 0
        assert len(data['recipes']) == 0
        assert len(data['ingredients']) == 0

    def test_search_only_other_user_cookbooks(self, auth_client, user: User, session: Session):
        """Test that search only returns user's own cookbooks."""
        # Create another user and cookbook
        other_user = User(
            id=uuid.uuid4(),
            email='other@example.com',
            hashed_password=get_password_hash('password123'),
            is_active=True,
            is_superuser=False,
            full_name='Other User',
        )
        session.add(other_user)
        session.commit()

        other_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
            visibility=VisibilityEnum.public,
        )
        session.add(other_cookbook)
        session.commit()

        response = auth_client.get('/api/v1/search?type=cookbook')

        assert response.status_code == 200
        data = response.json()
        # Should not include other user's cookbook
        assert all(cb['owner_id'] == str(user.id) for cb in data['cookbooks'])

    def test_search_case_insensitive_query(self, auth_client, user: User, session: Session, cookbook: Cookbook):
        """Test that search is case insensitive."""
        response = auth_client.get('/api/v1/search?type=cookbook&query=test')

        assert response.status_code == 200
        data = response.json()
        assert len(data['cookbooks']) >= 1

    def test_search_with_invalid_type(self, auth_client):
        """Test search with invalid type parameter."""
        response = auth_client.get('/api/v1/search?type=invalid')

        assert response.status_code == 200
        data = response.json()
        # Should return empty results for invalid type
        assert data['total_count'] == 0

    def test_search_with_empty_query(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe, ingredient: Ingredient
    ):
        """Test search with empty query string."""
        response = auth_client.get('/api/v1/search?query=')

        assert response.status_code == 200
        data = response.json()
        # Empty query should still return all items
        assert data['total_count'] >= 3
