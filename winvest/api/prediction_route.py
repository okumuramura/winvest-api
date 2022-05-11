from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, HTTPException, Path

from winvest import moex_cache
from winvest.api import PREDICTION_METHODS, logger
from winvest.manager import history_manage, stock_manage
from winvest.models import response_model

router = APIRouter()


@router.get(
    '/{stock_id}',
    status_code=HTTPStatus.OK,
    response_model=response_model.Methods,
)
async def predict_handler(stock_id: int = Path(..., ge=1)) -> Any:
    stock = stock_manage.get_by_id(stock_id=stock_id)

    if stock is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    cached_predictions = moex_cache.get_predictions(stock_id)

    if cached_predictions is not None:
        return cached_predictions.value

    history = await history_manage.load_up(stock)

    methods = []

    for method in PREDICTION_METHODS:
        try:
            prediction = method(history=history)
            methods.append(prediction)
        except Exception:  # pylint: disable=W0703
            logger.warning('error in prediction method %s', method.__name__)

    methods_model = response_model.Methods(methods=methods)
    moex_cache.save_predisctions(stock_id, methods_model)

    return methods_model
