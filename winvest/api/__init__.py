from http import HTTPStatus
from typing import Optional
import logging

from fastapi import HTTPException

from winvest.models.db import User

logger = logging.Logger(__name__)


def auth() -> Optional[User]:
    return None


def strict_auth() -> User:
    raise HTTPException(status_code=HTTPStatus.FORBIDDEN)
