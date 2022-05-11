from http import HTTPStatus

from fastapi.testclient import TestClient


def test_register_no_body(client: TestClient, fake_db):
    response = client.post('/register')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_register_ok(client: TestClient, fake_db, unregister_user):
    response = client.post('/register', json=unregister_user)
    assert response.status_code == HTTPStatus.CREATED


def test_register_already_registered(client: TestClient, fake_db, register_user):
    response = client.post('/register', json=register_user)
    assert response.status_code == HTTPStatus.CONFLICT
