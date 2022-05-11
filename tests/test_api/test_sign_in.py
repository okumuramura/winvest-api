from http import HTTPStatus

from fastapi.testclient import TestClient


def test_unregistered_sign_in(client: TestClient, fake_db, unregister_user):
    response = client.post('/login', json=unregister_user)
    assert response.status_code == HTTPStatus.CONFLICT


def test_registered_sign_in(client: TestClient, fake_db, register_user):
    response = client.post('/login', json=register_user)
    assert response.status_code == HTTPStatus.OK
