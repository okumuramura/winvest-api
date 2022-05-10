from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from winvest.api import HEADERS, logger
from winvest.manager import user_manage
from winvest.models import request_models

router = APIRouter()


@router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
    description='Register new user by login and password in body',
)
async def register_handler(request_user: request_models.User) -> Any:
    user_id = user_manage.register(request_user.login, request_user.password)
    if user_id is None:
        raise HTTPException(status_code=HTTPStatus.CONFLICT)
    logger.info('new user registered: %s', request_user.login)
    return JSONResponse({'detail': 'ok'}, headers=HEADERS)


@router.post(
    '/login',
    status_code=status.HTTP_200_OK,
    description='Sign in by login and password in body',
)
async def login_handler(request_user: request_models.User) -> Any:
    token = user_manage.sign_in(request_user.login, request_user.password)
    if token is None:
        raise HTTPException(status_code=HTTPStatus.CONFLICT)

    return JSONResponse(content={'token': token.token}, headers=HEADERS)
