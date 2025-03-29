from fastapi.testclient import TestClient

from app.main import app
from app.models import CookbookCreate

client = TestClient(app)


def test_create_item():
    new_item = CookbookCreate(cover='test', thumbnail='test', title='test', description='test')
    response = client.post('/api/v1/cookbooks/', json=new_item.__dict__)
    assert response.status_code == 200
    assert response.json() == new_item
