from http import HTTPStatus

from fastapi import APIRouter, Depends, Query

from winvest.api import strict_auth
from winvest.models import response_model, db
from winvest.manager import portfolio_manage

router = APIRouter()


@router.get(
    '/', status_code=HTTPStatus.OK, response_model=response_model.Portfolio
)
async def portfolio_handler(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: db.User = Depends(strict_auth),
):
    portfolio = await portfolio_manage.get_by_user(user.id, offset, limit)
    portfolio.username = user.login
    return portfolio
