from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, HTTPException

from winvest.manager import history_manage, stock_manage
from winvest.models import response_model

router = APIRouter()


@router.get(
    '/stocks/{stock_id}',
    status_code=HTTPStatus.OK,
    response_model=response_model.History,
    description='Return historical data for the selected instrument',
)
async def history_handler(stock_id: int) -> Any:
    stock = stock_manage.get_by_id(stock_id)

    if not stock:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    return await history_manage.load_up(stock)
