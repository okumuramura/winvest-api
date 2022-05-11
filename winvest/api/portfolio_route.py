from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Body

from winvest.api import strict_auth
from winvest.manager import portfolio_manage, stock_manage
from winvest.models import db, response_model

router = APIRouter()


@router.get(
    '/', status_code=HTTPStatus.OK, response_model=response_model.Portfolio
)
async def portfolio_handler(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: db.User = Depends(strict_auth),
) -> Any:
    portfolio = await portfolio_manage.get_by_user(user.id, offset, limit)
    portfolio.username = user.login
    return portfolio


@router.post('/add/{stock_id}', status_code=HTTPStatus.OK)
async def add_stock_handler(
    stock_id: int,
    quantity: int = Body(..., embed=True, ge=1),
    user: db.User = Depends(strict_auth),
) -> Any:
    stock = stock_manage.get_by_id(stock_id)
    if stock is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    portfolio = await portfolio_manage.add_stock(user, stock, quantity=quantity)

    if not portfolio:
        raise HTTPException(status_code=HTTPStatus.CONFLICT)


@router.delete('/{stock_id}', status_code=HTTPStatus.OK)
async def remove_stock_handler(
    stock_id: int, user: db.User = Depends(strict_auth)
) -> Any:
    if not portfolio_manage.remove_stock(user, stock_id):
        raise HTTPException(status_code=HTTPStatus.CONFLICT)
