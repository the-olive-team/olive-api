import uuid

import pytest
from sqlmodel import Session

from app.models import Ingredient


@pytest.fixture(name='ingredient')
def ingredient_fixture(session: Session) -> Ingredient:
    ingredient = Ingredient(
        id=uuid.uuid4(),
        ingredient='Test Ingredient',
        description='A test ingredient for unit tests',
        image='test-image.jpg',
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


class TestCreateIngredient:
    def test_create_ingredient_success(self, auth_client):
        """Test successful ingredient creation."""
        ingredient_data = {
            'ingredient': 'Salt',
            'description': 'Table salt for seasoning',
            'image': 'salt.jpg',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 200
        data = response.json()
        assert data['ingredient'] == ingredient_data['ingredient']
        assert data['description'] == ingredient_data['description']
        assert data['image'] == ingredient_data['image']
        assert 'id' in data

    def test_create_ingredient_minimal_data(self, auth_client):
        """Test ingredient creation with minimal required data."""
        ingredient_data = {
            'ingredient': 'Pepper',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 200
        data = response.json()
        assert data['ingredient'] == ingredient_data['ingredient']
        assert data['description'] is None
        assert data['image'] is None
        assert 'id' in data

    def test_create_ingredient_without_auth(self, client):
        """Test ingredient creation without authentication."""
        ingredient_data = {
            'ingredient': 'Salt',
            'description': 'Table salt for seasoning',
        }

        response = client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 401

    def test_create_ingredient_invalid_data(self, auth_client):
        """Test ingredient creation with invalid data."""
        # Missing required field
        ingredient_data = {
            'description': 'Missing ingredient name',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 422

    def test_create_ingredient_field_length_validation(self, auth_client):
        """Test ingredient creation with field length validation."""
        # Test ingredient name too long
        ingredient_data = {
            'ingredient': 'x' * 51,  # Exceeds max_length=50
            'description': 'Valid description',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 422

        # Test description too long
        ingredient_data = {
            'ingredient': 'Valid ingredient',
            'description': 'x' * 256,  # Exceeds max_length=255
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 422

        # Test image too long
        ingredient_data = {
            'ingredient': 'Valid ingredient',
            'image': 'x' * 1025,  # Exceeds max_length=1024
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 422


class TestGetIngredients:
    def test_get_ingredients_success(self, auth_client, session: Session):
        """Test successful retrieval of ingredients list."""
        # Create test ingredients
        ingredients = [
            Ingredient(ingredient='Salt', description='Table salt'),
            Ingredient(ingredient='Pepper', description='Black pepper'),
            Ingredient(ingredient='Sugar', description='White sugar'),
        ]
        for ingredient in ingredients:
            session.add(ingredient)
        session.commit()

        response = auth_client.get('/api/v1/ingredients/')

        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'count' in data
        assert data['count'] == 3
        assert len(data['data']) == 3

    def test_get_ingredients_pagination(self, auth_client, session: Session):
        """Test ingredients list pagination."""
        # Create 5 test ingredients
        ingredients = [Ingredient(ingredient=f'Ingredient {i}', description=f'Description {i}') for i in range(5)]
        for ingredient in ingredients:
            session.add(ingredient)
        session.commit()

        # Test with offset and limit
        response = auth_client.get('/api/v1/ingredients/?offset=2&limit=2')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 5
        assert len(data['data']) == 2

    def test_get_ingredients_empty_list(self, auth_client):
        """Test ingredients list when no ingredients exist."""
        response = auth_client.get('/api/v1/ingredients/')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert len(data['data']) == 0

    def test_get_ingredients_without_auth(self, client):
        """Test ingredients list retrieval without authentication."""
        response = client.get('/api/v1/ingredients/')

        assert response.status_code == 401

    def test_get_ingredients_default_pagination(self, auth_client, session: Session):
        """Test default pagination parameters."""
        # Create 150 ingredients to test default limit
        ingredients = [Ingredient(ingredient=f'Ingredient {i}', description=f'Description {i}') for i in range(150)]
        for ingredient in ingredients:
            session.add(ingredient)
        session.commit()

        response = auth_client.get('/api/v1/ingredients/')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 150
        assert len(data['data']) == 100  # Default limit


class TestGetIngredientById:
    def test_get_ingredient_by_id_success(self, auth_client, ingredient: Ingredient):
        """Test successful retrieval of ingredient by ID."""
        response = auth_client.get(f'/api/v1/ingredients/{ingredient.id}')

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(ingredient.id)
        assert data['ingredient'] == ingredient.ingredient
        assert data['description'] == ingredient.description
        assert data['image'] == ingredient.image

    def test_get_ingredient_by_id_not_found(self, auth_client):
        """Test retrieval of non-existent ingredient."""
        fake_id = uuid.uuid4()
        response = auth_client.get(f'/api/v1/ingredients/{fake_id}')

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_get_ingredient_by_id_invalid_uuid(self, auth_client):
        """Test retrieval with invalid UUID format."""
        response = auth_client.get('/api/v1/ingredients/invalid-uuid')

        assert response.status_code == 422

    def test_get_ingredient_by_id_without_auth(self, client, ingredient: Ingredient):
        """Test ingredient retrieval without authentication."""
        response = client.get(f'/api/v1/ingredients/{ingredient.id}')

        assert response.status_code == 401


class TestIngredientDataIntegrity:
    def test_ingredient_field_types(self, auth_client):
        """Test that ingredient fields have correct types."""
        ingredient_data = {
            'ingredient': 'Test Ingredient',
            'description': 'Test Description',
            'image': 'test.jpg',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 200
        data = response.json()

        # Verify field types
        assert isinstance(data['id'], str)
        assert isinstance(data['ingredient'], str)
        assert isinstance(data['description'], str)
        assert isinstance(data['image'], str)

    def test_ingredient_nullable_fields(self, auth_client):
        """Test that nullable fields can be null."""
        ingredient_data = {
            'ingredient': 'Test Ingredient',
            'description': None,
            'image': None,
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 200
        data = response.json()
        assert data['description'] is None
        assert data['image'] is None

    def test_ingredient_uuid_format(self, auth_client):
        """Test that ingredient ID is a valid UUID."""
        ingredient_data = {
            'ingredient': 'Test Ingredient',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 200
        data = response.json()

        # Verify UUID format
        try:
            uuid.UUID(data['id'])
        except ValueError:
            pytest.fail(f'Invalid UUID format: {data["id"]}')


class TestIngredientEdgeCases:
    def test_create_ingredient_empty_strings(self, auth_client):
        """Test ingredient creation with empty strings."""
        ingredient_data = {
            'ingredient': '',  # Empty string should fail validation
            'description': '',
            'image': '',
        }

        response = auth_client.post('/api/v1/ingredients/', json=ingredient_data)

        assert response.status_code == 422

    def test_get_ingredients_large_offset(self, auth_client, session: Session):
        """Test ingredients list with offset larger than total count."""
        # Create only 2 ingredients
        ingredients = [Ingredient(ingredient=f'Ingredient {i}', description=f'Description {i}') for i in range(2)]
        for ingredient in ingredients:
            session.add(ingredient)
        session.commit()

        # Request with offset larger than total count
        response = auth_client.get('/api/v1/ingredients/?offset=10&limit=5')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        assert len(data['data']) == 0

    def test_get_ingredients_zero_limit(self, auth_client, session: Session):
        """Test ingredients list with zero limit."""
        # Create test ingredients
        ingredients = [Ingredient(ingredient=f'Ingredient {i}', description=f'Description {i}') for i in range(3)]
        for ingredient in ingredients:
            session.add(ingredient)
        session.commit()

        response = auth_client.get('/api/v1/ingredients/?limit=0')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 3
        assert len(data['data']) == 0
