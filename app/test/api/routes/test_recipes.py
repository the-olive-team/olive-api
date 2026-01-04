import base64
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
        owner_id=user.id,
        visibility=VisibilityEnum.private,
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
        description='Test description',
        owner_id=user.id,
        cookbook_id=cookbook.id,
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


def create_base64_image() -> str:
    """Create a base64 encoded test image."""
    # Create a simple 1x1 pixel PNG image
    image_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
        b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05'
        b'\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return base64.b64encode(image_bytes).decode('utf-8')


@pytest.fixture
def ensure_s3_bucket(mocked_aws):  # noqa: ARG001
    """Ensure S3 bucket exists in mocked AWS environment."""
    # Reset the S3Service singleton so it gets reinitialized with mocked AWS
    import app.core.s3 as s3_module

    s3_module._s3_service = None

    # Force initialization of S3Service to create the bucket in mocked environment
    from app.core.s3 import s3_service

    _ = s3_service.client  # Access client to trigger initialization

    yield


class TestUpdateRecipe:
    def test_update_recipe_success(
        self,
        auth_client,
        user: User,
        session: Session,
        cookbook: Cookbook,
        recipe: Recipe,
        ingredient: Ingredient,
        ensure_s3_bucket,
    ):
        """Test successful recipe update."""
        image_base64 = create_base64_image()
        update_data = {
            'cookbook_uuid': str(cookbook.id),
            'title': 'Updated Recipe',
            'description': 'Updated description',
            'cloned_from': None,
            'tags': ['tag1', 'tag2'],
            'recipe_ingredients': [
                {
                    'quantity': 2,
                    'unit': 'cups',
                    'comments': 'You may need less',
                    'ingredient_id': str(ingredient.id),
                },
            ],
            'recipe_steps': [
                {
                    'step_instructions': 'First step instructions',
                    'step_picture': f'data:image/png;base64,{image_base64}',
                },
            ],
        }

        response = auth_client.put(f'/api/v1/recipies/{recipe.id}', json=update_data)

        assert response.status_code == 200


class TestCreateRecipeReference:
    def test_create_recipe_reference_success(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe
    ):
        """Test successful recipe reference creation."""
        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'John Doe',
        }

        response = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 200
        data = response.json()
        assert data['url'] == reference_data['url']
        assert data['author'] == reference_data['author']
        assert data['recipe_id'] == str(recipe.id)
        assert 'id' in data

    def test_create_recipe_reference_not_found(self, auth_client):
        """Test creating reference for non-existent recipe."""
        non_existent_id = uuid.uuid4()
        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'John Doe',
        }

        response = auth_client.post(f'/api/v1/recipies/{non_existent_id}/references', json=reference_data)

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_create_recipe_reference_other_user(self, auth_client, user: User, session: Session):
        """Test creating reference for another user's recipe."""
        # Create another user
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

        # Create cookbook and recipe for other user
        other_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
        )
        other_recipe = Recipe(
            id=uuid.uuid4(),
            title='Other Recipe',
            owner_id=other_user.id,
            cookbook_id=other_cookbook.id,
        )
        session.add(other_cookbook)
        session.add(other_recipe)
        session.commit()

        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'John Doe',
        }

        response = auth_client.post(f'/api/v1/recipies/{other_recipe.id}/references', json=reference_data)

        assert response.status_code == 403
        assert "doesn't have enough privileges" in response.json()['detail']

    def test_create_recipe_reference_without_auth(self, client: TestClient, recipe: Recipe):
        """Test creating reference without authentication."""
        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'John Doe',
        }

        response = client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 401

    def test_create_recipe_reference_invalid_uuid(self, auth_client):
        """Test creating reference with invalid UUID format."""
        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'John Doe',
        }

        response = auth_client.post('/api/v1/recipies/invalid-uuid/references', json=reference_data)

        assert response.status_code == 422

    def test_create_recipe_reference_missing_fields(self, auth_client, recipe: Recipe):
        """Test creating reference with missing required fields."""
        # Missing url
        reference_data = {
            'author': 'John Doe',
        }

        response = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 422

        # Missing author
        reference_data = {
            'url': 'https://example.com/recipe',
        }

        response = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 422

    def test_create_recipe_reference_long_fields(self, auth_client, recipe: Recipe):
        """Test creating reference with fields exceeding max length."""
        # URL too long
        reference_data = {
            'url': 'https://example.com/' + 'a' * 500,  # Exceeds max_length=512
            'author': 'John Doe',
        }

        response = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 422

        # Author too long
        reference_data = {
            'url': 'https://example.com/recipe',
            'author': 'a' * 256,  # Exceeds max_length=255
        }

        response = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference_data)

        assert response.status_code == 422

    def test_create_recipe_reference_multiple_references(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe
    ):
        """Test creating multiple references for the same recipe."""
        reference1_data = {
            'url': 'https://example.com/recipe1',
            'author': 'John Doe',
        }
        reference2_data = {
            'url': 'https://example.com/recipe2',
            'author': 'Jane Smith',
        }

        response1 = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference1_data)
        response2 = auth_client.post(f'/api/v1/recipies/{recipe.id}/references', json=reference2_data)

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()['url'] == reference1_data['url']
        assert response2.json()['url'] == reference2_data['url']
        assert response1.json()['id'] != response2.json()['id']

    def test_update_recipe_minimal_fields(
        self, auth_client, user: User, session: Session, cookbook: Cookbook, recipe: Recipe
    ):
        """Test recipe update with minimal fields."""
        update_data = {
            'cookbook_uuid': str(cookbook.id),
            'title': 'Minimal Recipe',
            'description': None,
            'cloned_from': None,
            'tags': [],
            'recipe_ingredients': [],
            'recipe_steps': [],
        }

        response = auth_client.put(f'/api/v1/recipies/{recipe.id}', json=update_data)

        assert response.status_code == 200
