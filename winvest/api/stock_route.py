from http import HTTPStatus
from typing import Optional, Any

from fastapi import APIRouter, Depends, Path, Query, HTTPException

from winvest.api import auth
from winvest.manager import stock_manage
from winvest.models import db, response_model

router = APIRouter()


@router.get(
    '/', status_code=HTTPStatus.OK, response_model=response_model.StockList
)
async def stocks_handler(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=50),
    user: Optional[db.User] = Depends(auth),
) -> Any:
    return await stock_manage.load_list(user, offset, limit)


@router.get(
    '/{stock_id}',
    status_code=HTTPStatus.OK,
    response_model=response_model.Stock,
)
async def stock_handler(
    stock_id: int = Path(..., ge=1), user: Optional[db.User] = Depends(auth)
) -> Any:
    stock = stock_manage.get_by_id(stock_id)

    if stock is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    with_price = await stock_manage.load_price(stock)

    if user is not None:
        owned_info = stock_manage.get_stock_data(user.id, stock_id)
        with_price.owned = owned_info.owned
        with_price.quantity = owned_info.quantity
        if with_price.price is not None:
            with_price.profit = (
                with_price.price * owned_info.quantity - owned_info.spent
            )

    return with_price
