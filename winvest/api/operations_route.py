from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, Query

from winvest.api import strict_auth
from winvest.manager import operation_manage
from winvest.models import db, response_model

router = APIRouter()


@router.get(
    '/',
    status_code=HTTPStatus.OK,
    response_model=response_model.OperationList,
)
def opeartions_handler(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=50),
    user: db.User = Depends(strict_auth),
) -> Any:
    return operation_manage.get_by_user(user.id, offset, limit)
