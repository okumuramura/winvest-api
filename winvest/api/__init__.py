import logging
from http import HTTPStatus
from typing import Optional

from fastapi import Header, HTTPException

from winvest.manager import user_manage
from winvest.models import db
from winvest.predictions.basic import (
    exponential_approximation,
    holt_win_fcast,
    linear_approximation,
    logarithmic_approximation,
    quadratic_approximation,
)

HEADERS = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, PATCH, DELETE',
    'Access-Control-Allow-Headers': 'X-Requested-With,content-type',
    'Access-Control-Allow-Origin': '*',
}

ALLOW_HISTORY_NONE = False

PREDICTION_METHODS = [
    linear_approximation,
    quadratic_approximation,
    logarithmic_approximation,
    exponential_approximation,
    holt_win_fcast,
]

logger = logging.Logger(__name__)


def auth(
    token: Optional[str] = Header(None, alias='authorization')
) -> Optional[db.User]:
    if not token:
        return None
    return user_manage.get_by_token(token)


def strict_auth(token: str = Header(..., alias='authorization')) -> db.User:
    user = user_manage.get_by_token(token)
    if not user:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)
    return user
