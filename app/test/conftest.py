import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models import User


class AuthenticatedTestClient(TestClient):
    """Test client that automatically includes authentication headers."""

    def __init__(self, app, user: User):
        super().__init__(app)
        self.user = user
        self._auth_headers = self._create_auth_headers()

    def _create_auth_headers(self):
        """Create authentication headers by overriding the current user dependency."""

        def get_current_user_override():
            return self.user

        app.dependency_overrides[get_current_user] = get_current_user_override
        return {}

    def get(self, url, **kwargs):
        """Override GET to automatically include auth headers."""
        kwargs.setdefault('headers', {}).update(self._auth_headers)
        return super().get(url, **kwargs)

    def post(self, url, **kwargs):
        """Override POST to automatically include auth headers."""
        kwargs.setdefault('headers', {}).update(self._auth_headers)
        return super().post(url, **kwargs)

    def put(self, url, **kwargs):
        """Override PUT to automatically include auth headers."""
        kwargs.setdefault('headers', {}).update(self._auth_headers)
        return super().put(url, **kwargs)

    def patch(self, url, **kwargs):
        """Override PATCH to automatically include auth headers."""
        kwargs.setdefault('headers', {}).update(self._auth_headers)
        return super().patch(url, **kwargs)

    def delete(self, url, **kwargs):
        """Override DELETE to automatically include auth headers."""
        kwargs.setdefault('headers', {}).update(self._auth_headers)
        return super().delete(url, **kwargs)


# Test database setup
@pytest.fixture(name='session')
def session_fixture() -> Generator[Session]:
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name='user')
def user_fixture(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email='test@example.com',
        hashed_password=get_password_hash('testpassword123'),
        is_active=True,
        is_superuser=False,
        full_name='Test User',
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name='client')
def client_fixture(session: Session) -> Generator[TestClient]:
    """Regular test client without authentication."""

    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name='auth_client')
def auth_client_fixture(session: Session, user: User) -> Generator[AuthenticatedTestClient]:
    """Authenticated test client that automatically includes auth headers."""

    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = AuthenticatedTestClient(app, user)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name='superuser')
def superuser_fixture(session: Session) -> User:
    """Create a superuser for testing admin functionality."""
    user = User(
        id=uuid.uuid4(),
        email='admin@example.com',
        hashed_password=get_password_hash('adminpassword123'),
        is_active=True,
        is_superuser=True,
        full_name='Admin User',
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name='superuser_client')
def superuser_client_fixture(session: Session, superuser: User) -> Generator[AuthenticatedTestClient]:
    """Authenticated test client with superuser privileges."""

    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = AuthenticatedTestClient(app, superuser)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mocked_aws():
    """Mocked AWS with arbitrary S3 settings"""
    settings.S3_ENDPOINT_URL = None
    settings.S3_ACCESS_KEY_ID = 'testing'
    settings.S3_SECRET_ACCESS_KEY = 'testing'
    settings.S3_REGION = 'testing'
    settings.S3_USE_SSL = 'testing'
    settings.S3_BUCKET_NAME = 'testing'
    with mock_aws():
        yield
