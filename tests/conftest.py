import pytest
from fastapi.testclient import TestClient

from winvest.api.serve import app


@pytest.fixture(scope='session')
def client():
    return TestClient(app)
