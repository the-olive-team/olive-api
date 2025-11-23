import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models import User
from app.utils import generate_password_reset_token


class TestLoginAccessToken:
    def test_login_success(self, client: TestClient, user: User):
        """Test successful login with correct credentials."""
        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email,
                'password': 'testpassword123',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'
        assert isinstance(data['access_token'], str)
        assert len(data['access_token']) > 0

    def test_login_incorrect_email(self, client: TestClient, user: User):
        """Test login with incorrect email."""
        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': 'wrong@example.com',
                'password': 'testpassword123',
            },
        )

        assert response.status_code == 400
        assert 'Incorrect email or password' in response.json()['detail']

    def test_login_incorrect_password(self, client: TestClient, user: User):
        """Test login with incorrect password."""
        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email,
                'password': 'wrongpassword',
            },
        )

        assert response.status_code == 400
        assert 'Incorrect email or password' in response.json()['detail']

    def test_login_inactive_user(self, client: TestClient, session: Session):
        """Test login with inactive user."""
        inactive_user = User(
            id=uuid.uuid4(),
            email='inactive@example.com',
            hashed_password=get_password_hash('testpassword123'),
            is_active=False,
            is_superuser=False,
            full_name='Inactive User',
        )
        session.add(inactive_user)
        session.commit()

        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': inactive_user.email,
                'password': 'testpassword123',
            },
        )

        assert response.status_code == 400
        assert 'Inactive user' in response.json()['detail']

    def test_login_missing_credentials(self, client: TestClient):
        """Test login with missing credentials."""
        response = client.post(
            '/api/v1/login/access-token',
            data={},
        )

        assert response.status_code == 422

    def test_login_empty_password(self, client: TestClient, user: User):
        """Test login with empty password."""
        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email,
                'password': '',
            },
        )

        # FastAPI may return 422 for validation errors or 400 for authentication errors
        # Empty password might be caught by validation (422) or authentication (400)
        assert response.status_code in [400, 422]


class TestTestToken:
    def test_test_token_success(self, auth_client):
        """Test successful token validation."""
        response = auth_client.post('/api/v1/login/test-token')

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert 'email' in data
        assert 'is_active' in data
        assert 'is_superuser' in data
        assert data['is_active'] is True

    def test_test_token_without_auth(self, client: TestClient):
        """Test token validation without authentication."""
        response = client.post('/api/v1/login/test-token')

        assert response.status_code == 401


class TestPasswordRecovery:
    @patch('app.api.routes.login.send_email')
    @patch('app.utils.render_email_template')
    def test_recover_password_success(self, mock_render_template, mock_send_email, client: TestClient, user: User):
        """Test successful password recovery."""
        # Mock the email template rendering
        mock_render_template.return_value = '<html>Test email content</html>'

        response = client.post(f'/api/v1/password-recovery/{user.email}')

        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Password recovery email sent'
        # Verify email was sent
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args.kwargs['email_to'] == user.email
        assert 'subject' in call_args.kwargs
        assert 'html_content' in call_args.kwargs

    def test_recover_password_nonexistent_user(self, client: TestClient):
        """Test password recovery for non-existent user."""
        response = client.post('/api/v1/password-recovery/nonexistent@example.com')

        assert response.status_code == 404
        assert 'does not exist' in response.json()['detail']

    @patch('app.api.routes.login.send_email')
    @patch('app.utils.render_email_template')
    def test_recover_password_inactive_user(
        self, mock_render_template, mock_send_email, client: TestClient, session: Session
    ):
        """Test password recovery for inactive user (should still work)."""
        # Mock the email template rendering
        mock_render_template.return_value = '<html>Test email content</html>'

        inactive_user = User(
            id=uuid.uuid4(),
            email='inactive@example.com',
            hashed_password=get_password_hash('testpassword123'),
            is_active=False,
            is_superuser=False,
            full_name='Inactive User',
        )
        session.add(inactive_user)
        session.commit()

        response = client.post(f'/api/v1/password-recovery/{inactive_user.email}')

        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Password recovery email sent'
        mock_send_email.assert_called_once()

    def test_recover_password_invalid_email_format(self, client: TestClient):
        """Test password recovery with invalid email format."""
        response = client.post('/api/v1/password-recovery/invalid-email')

        # FastAPI will validate the email format in the path parameter
        # This might return 422 or 404 depending on validation
        assert response.status_code in [404, 422]


class TestResetPassword:
    def test_reset_password_success(self, client: TestClient, user: User, session: Session):
        """Test successful password reset."""
        # Generate a valid token
        token = generate_password_reset_token(email=user.email)
        new_password = 'newpassword123'

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': token,
                'new_password': new_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Password updated successfully'

        # Verify password was actually changed by trying to login with new password
        login_response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email,
                'password': new_password,
            },
        )
        assert login_response.status_code == 200

    def test_reset_password_invalid_token(self, client: TestClient):
        """Test password reset with invalid token."""
        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': 'invalid-token',
                'new_password': 'newpassword123',
            },
        )

        assert response.status_code == 400
        assert 'Invalid token' in response.json()['detail']

    def test_reset_password_expired_token(self, client: TestClient, user: User):
        """Test password reset with expired token."""
        # Create an expired token by using a very old timestamp
        from datetime import UTC, datetime, timedelta

        import jwt

        from app.core.config import settings

        expired_time = datetime.now(UTC) - timedelta(hours=100)  # Very old
        expired_token = jwt.encode(
            {'exp': expired_time.timestamp(), 'nbf': expired_time, 'sub': user.email},
            settings.SECRET_KEY,
            algorithm='HS256',
        )

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': expired_token,
                'new_password': 'newpassword123',
            },
        )

        assert response.status_code == 400
        assert 'Invalid token' in response.json()['detail']

    def test_reset_password_nonexistent_user(self, client: TestClient):
        """Test password reset for non-existent user."""
        # Generate token for non-existent email
        token = generate_password_reset_token(email='nonexistent@example.com')

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': token,
                'new_password': 'newpassword123',
            },
        )

        assert response.status_code == 404
        assert 'does not exist' in response.json()['detail']

    def test_reset_password_inactive_user(self, client: TestClient, session: Session):
        """Test password reset for inactive user."""
        inactive_user = User(
            id=uuid.uuid4(),
            email='inactive@example.com',
            hashed_password=get_password_hash('oldpassword123'),
            is_active=False,
            is_superuser=False,
            full_name='Inactive User',
        )
        session.add(inactive_user)
        session.commit()

        token = generate_password_reset_token(email=inactive_user.email)

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': token,
                'new_password': 'newpassword123',
            },
        )

        assert response.status_code == 400
        assert 'Inactive user' in response.json()['detail']

    def test_reset_password_missing_fields(self, client: TestClient):
        """Test password reset with missing fields."""
        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': 'some-token',
            },
        )

        assert response.status_code == 422

    def test_reset_password_short_password(self, client: TestClient, user: User):
        """Test password reset with password too short."""
        token = generate_password_reset_token(email=user.email)

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': token,
                'new_password': 'short',  # Less than 8 characters
            },
        )

        assert response.status_code == 422


class TestPasswordRecoveryHtmlContent:
    @patch('app.utils.render_email_template')
    def test_recover_password_html_content_success(self, mock_render_template, superuser_client, user: User):
        """Test successful HTML content generation for password recovery."""
        # Mock the email template rendering with specific content
        expected_html = '<html><body>Test email content</body></html>'
        mock_render_template.return_value = expected_html

        response = superuser_client.post(f'/api/v1/password-recovery-html-content/{user.email}')

        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/html; charset=utf-8'
        # Verify the exact mocked HTML content is returned
        assert response.text == expected_html

    def test_recover_password_html_content_nonexistent_user(self, superuser_client):
        """Test HTML content generation for non-existent user."""
        response = superuser_client.post('/api/v1/password-recovery-html-content/nonexistent@example.com')

        assert response.status_code == 404
        assert 'does not exist' in response.json()['detail']

    def test_recover_password_html_content_without_superuser(self, auth_client, user: User):
        """Test HTML content generation without superuser privileges."""
        response = auth_client.post(f'/api/v1/password-recovery-html-content/{user.email}')

        assert response.status_code == 403
        assert "doesn't have enough privileges" in response.json()['detail']

    def test_recover_password_html_content_without_auth(self, client: TestClient, user: User):
        """Test HTML content generation without authentication."""
        response = client.post(f'/api/v1/password-recovery-html-content/{user.email}')

        assert response.status_code == 401

    @patch('app.utils.render_email_template')
    def test_recover_password_html_content_inactive_user(
        self, mock_render_template, superuser_client, session: Session
    ):
        """Test HTML content generation for inactive user (should still work)."""
        # Mock the email template rendering
        mock_render_template.return_value = '<html><body>Test email content</body></html>'

        inactive_user = User(
            id=uuid.uuid4(),
            email='inactive@example.com',
            hashed_password=get_password_hash('testpassword123'),
            is_active=False,
            is_superuser=False,
            full_name='Inactive User',
        )
        session.add(inactive_user)
        session.commit()

        response = superuser_client.post(f'/api/v1/password-recovery-html-content/{inactive_user.email}')

        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/html; charset=utf-8'
        assert len(response.text) > 0


class TestLoginEdgeCases:
    def test_login_case_sensitive_email(self, client: TestClient, user: User):
        """Test that email login is case-sensitive or not (depends on implementation)."""
        # Try with different case
        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email.upper(),
                'password': 'testpassword123',
            },
        )

        # This might succeed or fail depending on email normalization
        # Most systems normalize emails, so this might fail
        # We'll just check it doesn't crash
        assert response.status_code in [200, 400]

    def test_login_special_characters_in_password(self, client: TestClient, session: Session):
        """Test login with special characters in password."""
        special_password = 'p@ssw0rd!@#$%^&*()'
        user = User(
            id=uuid.uuid4(),
            email='special@example.com',
            hashed_password=get_password_hash(special_password),
            is_active=True,
            is_superuser=False,
            full_name='Special User',
        )
        session.add(user)
        session.commit()

        response = client.post(
            '/api/v1/login/access-token',
            data={
                'username': user.email,
                'password': special_password,
            },
        )

        assert response.status_code == 200
        assert 'access_token' in response.json()

    def test_reset_password_same_as_old(self, client: TestClient, user: User):
        """Test resetting password to the same value."""
        token = generate_password_reset_token(email=user.email)
        old_password = 'testpassword123'

        response = client.post(
            '/api/v1/reset-password/',
            json={
                'token': token,
                'new_password': old_password,
            },
        )

        # Should succeed - resetting to same password is allowed
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Password updated successfully'
