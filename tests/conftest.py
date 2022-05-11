import os

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from winvest import Base
from winvest.api.serve import app
from winvest.models import db


@pytest.fixture(scope='session')
def client():
    return TestClient(app)


@pytest.fixture(scope='session')
def test_db():
    if os.path.exists('./test.db'):
        os.remove('./test.db')

    engine = create_engine('sqlite:///test.db')
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    yield TestSession
    os.remove('./test.db')


@pytest.fixture(scope='session')
def fake_db(test_db, session_mocker: MockerFixture):
    session_mocker.patch('winvest.manager.SessionCreator', test_db)


@pytest.fixture(scope='session')
def register_user(test_db, fake_db):
    data = {'login': 'test_user', 'password': 'test_password'}
    with test_db() as session:
        session: Session
        new_user = db.User(login=data['login'], password=data['password'])
        session.add(new_user)
        session.commit()
    return data


@pytest.fixture
def unregister_user(test_db, fake_db):
    data = {'login': 'unreg_user', 'password': 'some_password'}
    with test_db() as session:
        session: Session
        session.query(db.User).filter(db.User.login == data['login']).delete()
        session.commit()
    return data


@pytest.fixture(scope='session')
def invalid_user():
    return {'login': 'very_long_login_wooow', 'password': 'psd'}


@pytest.fixture(scope='session')
def valid_user_token(test_db, fake_db, register_user):
    with test_db() as session:
        session: Session
        user: db.User = (
            session.query(db.User)
            .filter(db.User.login == register_user['login'])
            .first()
        )
        token = db.Token(user)
        token_str = token.token
        session.add(token)
        session.commit()

    return token_str


@pytest.fixture(scope='session')
def fake_stocks(test_db):
    stocks = [db.Stock(f'TS{x}', 'test stock {x}') for x in range(10)]
    with test_db() as session:
        session: Session
        session.add_all(stocks)
        session.commit()

    return stocks


@pytest.fixture(scope='session')
def fake_cache(session_mocker: MockerFixture):
    cache_mock = session_mocker.patch('winvest.moex_cache')
    return cache_mock
