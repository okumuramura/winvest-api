import logging
from http import HTTPStatus
from typing import Optional

from fastapi import Header, HTTPException

from winvest.manager import user_manage
from winvest.models import db

HEADERS = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, PATCH, DELETE',
    'Access-Control-Allow-Headers': 'X-Requested-With,content-type',
    'Access-Control-Allow-Origin': '*',
}

ALLOW_HISTORY_NONE = False

logger = logging.Logger(__name__)


def auth(token: str = Header(..., alias='authorization')) -> Optional[db.User]:
    return user_manage.get_by_token(token)


def strict_auth(token: str = Header(..., alias='authorization')) -> db.User:
    user = user_manage.get_by_token(token)
    if not user:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)
    return user
