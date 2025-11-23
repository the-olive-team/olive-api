import io
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models import Cookbook, User, VisibilityEnum


class TestCreateCookbook:
    def test_create_cookbook_success(self, auth_client, user: User, mocked_aws):
        """Test successful cookbook creation with images."""
        cover_file = io.BytesIO(b'fake cover image')
        thumbnail_file = io.BytesIO(b'fake thumbnail image')

        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'title': 'My First Cookbook',
                'description': 'A collection of my favorite recipes',
                'visibility': VisibilityEnum.private.value,
            },
            files={
                'cover': ('cover.jpg', cover_file, 'image/jpeg'),
                'thumbnail': ('thumb.jpg', thumbnail_file, 'image/jpeg'),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'My First Cookbook'
        assert data['description'] == 'A collection of my favorite recipes'
        assert data['cover'] is not None
        assert data['thumbnail'] is not None
        assert data['owner_id'] == str(user.id)
        assert 'id' in data
        assert data['visibility'] == VisibilityEnum.private.value

    def test_create_cookbook_minimal_fields(self, auth_client, user: User):
        """Test cookbook creation with only required fields."""
        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'title': 'Minimal Cookbook',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Minimal Cookbook'
        assert data['owner_id'] == str(user.id)
        assert data['description'] is None
        assert data['cover'] is None
        assert data['thumbnail'] is None

    def test_create_cookbook_without_auth(self, client: TestClient):
        """Test cookbook creation without authentication."""
        response = client.post(
            '/api/v1/cookbooks/',
            data={
                'title': 'Unauthorized Cookbook',
            },
        )

        assert response.status_code == 401

    def test_create_cookbook_missing_title(self, auth_client):
        """Test cookbook creation without required title field."""
        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'description': 'Missing title',
            },
        )

        assert response.status_code == 422

    def test_create_cookbook_empty_title(self, auth_client, user: User):
        """Test cookbook creation with empty title (empty strings may be allowed)."""
        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'title': '',
            },
        )

        # Empty strings might be allowed by the model validation
        # If it's 200, empty title is allowed; if 422, it's rejected
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data['title'] == ''
            assert data['owner_id'] == str(user.id)

    def test_create_cookbook_long_fields(self, auth_client):
        """Test cookbook creation with fields exceeding max length."""
        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'title': 'a' * 51,  # Exceeds max_length=50
                'description': 'b' * 256,  # Exceeds max_length=255
            },
        )

        assert response.status_code == 422


class TestGetCookbooks:
    def test_get_cookbooks_success(self, auth_client, user: User, session: Session):
        """Test successful retrieval of cookbooks."""
        # Create some cookbooks
        cookbook1 = Cookbook(
            id=uuid.uuid4(),
            title='Cookbook 1',
            owner_id=user.id,
            visibility=VisibilityEnum.private,
        )
        cookbook2 = Cookbook(
            id=uuid.uuid4(),
            title='Cookbook 2',
            owner_id=user.id,
            visibility=VisibilityEnum.public,
        )
        session.add(cookbook1)
        session.add(cookbook2)
        session.commit()

        response = auth_client.get('/api/v1/cookbooks/')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        assert len(data['data']) == 2
        titles = [cb['title'] for cb in data['data']]
        assert 'Cookbook 1' in titles
        assert 'Cookbook 2' in titles

    def test_get_cookbooks_empty(self, auth_client):
        """Test getting cookbooks when user has none."""
        response = auth_client.get('/api/v1/cookbooks/')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert len(data['data']) == 0

    def test_get_cookbooks_only_own(self, auth_client, user: User, session: Session):
        """Test that users only see their own cookbooks."""
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

        # Create cookbooks for both users
        own_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='My Cookbook',
            owner_id=user.id,
        )
        other_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
        )
        session.add(own_cookbook)
        session.add(other_cookbook)
        session.commit()

        response = auth_client.get('/api/v1/cookbooks/')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert len(data['data']) == 1
        assert data['data'][0]['title'] == 'My Cookbook'
        assert data['data'][0]['owner_id'] == str(user.id)

    def test_get_cookbooks_pagination(self, auth_client, user: User, session: Session):
        """Test cookbook pagination."""
        # Create multiple cookbooks
        for i in range(5):
            cookbook = Cookbook(
                id=uuid.uuid4(),
                title=f'Cookbook {i}',
                owner_id=user.id,
            )
            session.add(cookbook)
        session.commit()

        # Test with limit
        response = auth_client.get('/api/v1/cookbooks/?limit=2')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 5
        assert len(data['data']) == 2

        # Test with offset
        response = auth_client.get('/api/v1/cookbooks/?offset=2&limit=2')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 5
        assert len(data['data']) == 2

    def test_get_cookbooks_without_auth(self, client: TestClient):
        """Test getting cookbooks without authentication."""
        response = client.get('/api/v1/cookbooks/')

        assert response.status_code == 401


class TestGetCookbook:
    def test_get_cookbook_success(self, auth_client, user: User, session: Session):
        """Test successful retrieval of a single cookbook."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='My Cookbook',
            description='Test description',
            owner_id=user.id,
            visibility=VisibilityEnum.public,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.get(f'/api/v1/cookbooks/{cookbook.id}')

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(cookbook.id)
        assert data['title'] == 'My Cookbook'
        assert data['description'] == 'Test description'
        assert data['owner_id'] == str(user.id)
        assert data['visibility'] == VisibilityEnum.public.value

    def test_get_cookbook_not_found(self, auth_client):
        """Test getting a non-existent cookbook."""
        non_existent_id = uuid.uuid4()
        response = auth_client.get(f'/api/v1/cookbooks/{non_existent_id}')

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_get_cookbook_other_user(self, auth_client, user: User, session: Session):
        """Test getting a cookbook owned by another user."""
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

        # Create cookbook for other user
        other_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
        )
        session.add(other_cookbook)
        session.commit()

        response = auth_client.get(f'/api/v1/cookbooks/{other_cookbook.id}')

        assert response.status_code == 403
        assert "doesn't have enough privileges" in response.json()['detail']

    def test_get_cookbook_without_auth(self, client: TestClient, user: User, session: Session):
        """Test getting a cookbook without authentication."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = client.get(f'/api/v1/cookbooks/{cookbook.id}')

        assert response.status_code == 401

    def test_get_cookbook_invalid_uuid(self, auth_client):
        """Test getting a cookbook with invalid UUID format."""
        response = auth_client.get('/api/v1/cookbooks/invalid-uuid')

        assert response.status_code == 422


class TestDeleteCookbook:
    def test_delete_cookbook_success(self, auth_client, user: User, session: Session):
        """Test successful cookbook deletion."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Cookbook to Delete',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.delete(f'/api/v1/cookbooks/{cookbook.id}')

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(cookbook.id)
        assert data['title'] == 'Cookbook to Delete'

        # Verify it's actually deleted
        deleted_cookbook = session.get(Cookbook, cookbook.id)
        assert deleted_cookbook is None

    def test_delete_cookbook_not_found(self, auth_client):
        """Test deleting a non-existent cookbook."""
        non_existent_id = uuid.uuid4()
        response = auth_client.delete(f'/api/v1/cookbooks/{non_existent_id}')

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_delete_cookbook_other_user(self, auth_client, user: User, session: Session):
        """Test deleting a cookbook owned by another user."""
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

        # Create cookbook for other user
        other_cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
        )
        session.add(other_cookbook)
        session.commit()

        response = auth_client.delete(f'/api/v1/cookbooks/{other_cookbook.id}')

        assert response.status_code == 403
        assert "doesn't have enough privileges" in response.json()['detail']

        # Verify cookbook still exists
        existing_cookbook = session.get(Cookbook, other_cookbook.id)
        assert existing_cookbook is not None

    def test_delete_cookbook_without_auth(self, client: TestClient, user: User, session: Session):
        """Test deleting a cookbook without authentication."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = client.delete(f'/api/v1/cookbooks/{cookbook.id}')

        assert response.status_code == 401

        # Verify cookbook still exists
        existing_cookbook = session.get(Cookbook, cookbook.id)
        assert existing_cookbook is not None

    def test_delete_cookbook_invalid_uuid(self, auth_client):
        """Test deleting a cookbook with invalid UUID format."""
        response = auth_client.delete('/api/v1/cookbooks/invalid-uuid')

        assert response.status_code == 422


class TestSaveCookbook:
    def test_save_cookbook_success(self, auth_client, user: User, session: Session):
        """Test successful cookbook save."""
        # Create a cookbook owned by another user (to save it)
        other_user = User(
            id=uuid.uuid4(),
            email='owner@example.com',
            hashed_password=get_password_hash('password123'),
            is_active=True,
            is_superuser=False,
            full_name='Owner User',
        )
        session.add(other_user)
        session.commit()

        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Cookbook to Save',
            owner_id=other_user.id,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.post(f'/api/v1/cookbooks/{cookbook.id}/save')

        assert response.status_code == 200
        data = response.json()
        assert data['user_id'] == str(user.id)
        assert data['cookbook_id'] == str(cookbook.id)
        # Note: CookbookSaveCreate response model doesn't include id field

    def test_save_cookbook_not_found(self, auth_client):
        """Test saving a non-existent cookbook."""
        non_existent_id = uuid.uuid4()
        response = auth_client.post(f'/api/v1/cookbooks/{non_existent_id}/save')

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_save_cookbook_without_auth(self, client: TestClient, user: User, session: Session):
        """Test saving a cookbook without authentication."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = client.post(f'/api/v1/cookbooks/{cookbook.id}/save')

        assert response.status_code == 401

    def test_save_cookbook_invalid_uuid(self, auth_client):
        """Test saving a cookbook with invalid UUID format."""
        response = auth_client.post('/api/v1/cookbooks/invalid-uuid/save')

        assert response.status_code == 422

    def test_save_cookbook_own_cookbook(self, auth_client, user: User, session: Session):
        """Test saving own cookbook (should still work)."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='My Own Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.post(f'/api/v1/cookbooks/{cookbook.id}/save')

        # Should succeed - users can save their own cookbooks
        assert response.status_code == 200
        data = response.json()
        assert data['user_id'] == str(user.id)
        assert data['cookbook_id'] == str(cookbook.id)
        # Note: CookbookSaveCreate response model doesn't include id field


class TestCookbookEdgeCases:
    def test_create_cookbook_special_characters(self, auth_client, user: User):
        """Test cookbook creation with special characters in title."""
        response = auth_client.post(
            '/api/v1/cookbooks/',
            data={
                'title': 'Cookbook & Recipes! 🍳',
                'description': 'Special chars: <>&"\'',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Cookbook & Recipes! 🍳'
        assert data['description'] == 'Special chars: <>&"\''

    def test_get_cookbooks_large_limit(self, auth_client, user: User, session: Session):
        """Test getting cookbooks with a very large limit."""
        # Create a few cookbooks
        for i in range(3):
            cookbook = Cookbook(
                id=uuid.uuid4(),
                title=f'Cookbook {i}',
                owner_id=user.id,
            )
            session.add(cookbook)
        session.commit()

        response = auth_client.get('/api/v1/cookbooks/?limit=1000')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 3
        assert len(data['data']) == 3

    def test_get_cookbooks_negative_offset(self, auth_client):
        """Test getting cookbooks with negative offset."""
        response = auth_client.get('/api/v1/cookbooks/?offset=-1')

        # Should handle gracefully - might return 422 or default to 0
        assert response.status_code in [200, 422]

    def test_get_cookbooks_zero_limit(self, auth_client, user: User, session: Session):
        """Test getting cookbooks with zero limit."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.get('/api/v1/cookbooks/?limit=0')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert len(data['data']) == 0  # Limit of 0 should return empty list


class TestUpdateCookbook:
    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_fields(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test updating cookbook text fields."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Original Title',
            description='Original description',
            owner_id=user.id,
            visibility=VisibilityEnum.private,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={
                'title': 'Updated Title',
                'description': 'Updated description',
                'visibility': VisibilityEnum.public.value,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Title'
        assert data['description'] == 'Updated description'
        assert data['visibility'] == VisibilityEnum.public.value

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_upload_cover(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test uploading cover image via update endpoint."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        mock_s3_service.upload_file.return_value = 'cookbooks/test/cover-123.jpg'
        cover_file = io.BytesIO(b'fake cover image')

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={},
            files={'cover': ('cover.jpg', cover_file, 'image/jpeg')},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['cover'] is not None
        assert 'cover' in data['cover']
        mock_s3_service.upload_file.assert_called_once()

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_replace_cover(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test replacing existing cover image via update endpoint."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
            cover='cookbooks/test/old-cover.jpg',
        )
        session.add(cookbook)
        session.commit()

        mock_s3_service.upload_file.return_value = 'cookbooks/test/new-cover.jpg'
        cover_file = io.BytesIO(b'new cover image')

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={},
            files={'cover': ('cover.jpg', cover_file, 'image/jpeg')},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['cover'] != 'cookbooks/test/old-cover.jpg'
        mock_s3_service.delete_file.assert_called_once_with('cookbooks/test/old-cover.jpg')
        mock_s3_service.upload_file.assert_called_once()

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_delete_cover(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test deleting cover image via update endpoint."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
            cover='cookbooks/test/cover.jpg',
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={'delete_cover': 'true'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['cover'] is None
        mock_s3_service.delete_file.assert_called_once_with('cookbooks/test/cover.jpg')

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_upload_thumbnail(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test uploading thumbnail image via update endpoint."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        mock_s3_service.upload_file.return_value = 'cookbooks/test/thumbnail-123.jpg'
        thumbnail_file = io.BytesIO(b'fake thumbnail image')

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={},
            files={'thumbnail': ('thumbnail.jpg', thumbnail_file, 'image/jpeg')},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['thumbnail'] is not None
        mock_s3_service.upload_file.assert_called_once()

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_delete_thumbnail(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test deleting thumbnail image via update endpoint."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
            thumbnail='cookbooks/test/thumbnail.jpg',
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={'delete_thumbnail': 'true'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['thumbnail'] is None
        mock_s3_service.delete_file.assert_called_once_with('cookbooks/test/thumbnail.jpg')

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_combined(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test updating fields and images together."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Original Title',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        mock_s3_service.upload_file.return_value = 'cookbooks/test/cover-123.jpg'
        cover_file = io.BytesIO(b'fake cover')

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={
                'title': 'Updated Title',
                'description': 'New description',
            },
            files={'cover': ('cover.jpg', cover_file, 'image/jpeg')},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Title'
        assert data['description'] == 'New description'
        assert data['cover'] is not None

    def test_update_cookbook_not_found(self, auth_client):
        """Test updating non-existent cookbook."""
        non_existent_id = uuid.uuid4()
        response = auth_client.patch(
            f'/api/v1/cookbooks/{non_existent_id}',
            data={'title': 'New Title'},
        )

        assert response.status_code == 404

    def test_update_cookbook_other_user(self, auth_client, user: User, session: Session):
        """Test updating another user's cookbook."""
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

        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Other Cookbook',
            owner_id=other_user.id,
        )
        session.add(cookbook)
        session.commit()

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={'title': 'Hacked Title'},
        )

        assert response.status_code == 403

    def test_update_cookbook_invalid_file_type(self, auth_client, user: User, session: Session):
        """Test uploading non-image file via update."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        text_file = io.BytesIO(b'not an image')

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={},
            files={'cover': ('document.txt', text_file, 'text/plain')},
        )

        assert response.status_code == 400
        assert 'image' in response.json()['detail'].lower()

    @patch('app.api.routes.cookbooks.s3_service')
    def test_update_cookbook_large_file(self, mock_s3_service, auth_client, user: User, session: Session):
        """Test uploading file that exceeds size limit via update."""
        cookbook = Cookbook(
            id=uuid.uuid4(),
            title='Test Cookbook',
            owner_id=user.id,
        )
        session.add(cookbook)
        session.commit()

        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        large_file = io.BytesIO(large_content)

        response = auth_client.patch(
            f'/api/v1/cookbooks/{cookbook.id}',
            data={},
            files={'cover': ('large.jpg', large_file, 'image/jpeg')},
        )

        assert response.status_code == 400
        assert 'size' in response.json()['detail'].lower()
        mock_s3_service.upload_file.assert_not_called()
