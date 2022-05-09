from http import HTTPStatus
from typing import Optional, Any

from fastapi import HTTPException, Header, APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
import bcrypt

from winvest.models import db, request_models
from winvest.api.manager import Manager
from winvest.api import HEADERS, logger

router = APIRouter()
manager = Manager('sqlite:///database.db')


def auth(token: str = Header(..., alias='authorization')) -> Optional[db.User]:
    return None


def strict_auth(token: str = Header(..., alias='authorization')) -> db.User:
    raise HTTPException(status_code=HTTPStatus.FORBIDDEN)


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register_handler(request_user: request_models.User) -> Any:
    password_hash = bcrypt.hashpw(request_user.password, bcrypt.gensalt(10))
    user = db.User(request_user.login, password_hash)
    manager.session.add(user)
    try:
        manager.session.commit()
    except IntegrityError:
        manager.session.rollback()
        raise HTTPException(
            status_code=406, detail='Login already exists', headers=HEADERS
        )

    logger.info('new user registered: %s', user.login)
    return JSONResponse({'detail': 'ok'}, headers=HEADERS)


@router.post('/login', status_code=status.HTTP_200_OK)
async def login_handler(request_user: request_models.User) -> Any:
    user: db.User = (
        manager.session.query(db.User)
        .filter(db.User.login == request_user.login)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=406, detail='User is not found', headers=HEADERS
        )

    if not bcrypt.checkpw(request_user.password, user.password):
        raise HTTPException(
            status_code=406, detail='Wrong password', headers=HEADERS
        )

    token = db.Token(user.id)

    manager.session.add(token)
    manager.session.commit()

    return JSONResponse(content={'token': token.token}, headers=HEADERS)
