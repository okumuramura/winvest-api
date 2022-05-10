import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Tuple

from fastapi import (
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from winvest import moex_client, moex_cache
from winvest.api import (
    HEADERS,
    ALLOW_HISTORY_NONE,
    authorization_route,
    history_route,
    logger,
    portfolio_route,
    strict_auth,
)
from winvest.api.manager import Manager
from winvest.models import db
from winvest.models.response_model import (
    History,
    Methods,
    Stock,
    StockList,
)
from winvest.predictions.basic import (
    exponential_approximation,
    holt_win_fcast,
    linear_approximation,
    logarithmic_approximation,
    quadratic_approximation,
)

app = FastAPI()
app.include_router(router=authorization_route.router)
app.include_router(router=history_route.router, prefix='/history')
app.include_router(router=portfolio_route.router, prefix='/portfolio')

manager = Manager('sqlite:///database.db')

origins = ['http://localhost:3000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)

PREDICTION_METHODS = [
    linear_approximation,
    quadratic_approximation,
    logarithmic_approximation,
    exponential_approximation,
    holt_win_fcast,
]


@app.get('/stocks', status_code=status.HTTP_200_OK, response_model=StockList)
async def stocks_handler(request: Request) -> Any:
    token = request.headers.get('Authorization', None)
    users_stocks: Dict[str, db.Portfolio] = {}
    if token is not None:
        db_token = (
            manager.session.query(db.Token)
            .filter(db.Token.token == token)
            .first()
        )
        if db_token is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Invalid token',
                headers=HEADERS,
            )
        user = db_token.user
        stocks: List[Tuple[db.Portfolio, db.Stock]] = (
            manager.session.query(db.Portfolio, db.Stock)
            .join(db.Stock)
            .filter(db.Portfolio.user_id == user.id)
            .all()
        )
        for p, s in stocks:
            users_stocks.update({s.shortname: p})

    api_stocks_list = await moex_client.actual()
    stocks_list = []
    for s in api_stocks_list:
        short = s[0]
        price = s[12]
        change = s[25]
        deals = s[54]
        stock_info: db.Stock = (
            manager.session.query(db.Stock)
            .filter(db.Stock.shortname == short)
            .first()
        )
        if stock_info is not None:
            stock = Stock(
                id=stock_info.id,
                fullname=stock_info.fullname,
                shortname=stock_info.shortname,
                currency=stock_info.currency,
                price=price,
                change=change,
                volume_of_deals=deals,
            )
            if stock_info.shortname in users_stocks:
                stock.owned = True
                _p = users_stocks[stock_info.shortname]
                stock.quantity = _p.quantity
                stock.profit = _p.quantity * price - _p.spent

            stocks_list.append(stock)
        else:
            logger.info('stock not in database: %s', short)

    stocks_list = sorted(
        stocks_list,
        # key=lambda x: x.shortname,
        key=lambda x: 0 if x.volume_of_deals is None else x.volume_of_deals,
        reverse=True,
    )

    logger.info('%d stocks returned in total', len(stocks_list))
    return Response(
        content=StockList(stocks=stocks_list).json(), headers=HEADERS
    )


@app.get('/stocks/{id}', status_code=status.HTTP_200_OK, response_model=Stock)
async def stock_handler(request: Request, id: int, h: bool = False) -> Any:
    token = request.headers.get('Authorization', None)
    user_stocks: Dict[str, db.Portfolio] = {}
    if token is not None:
        db_token = (
            manager.session.query(db.Token)
            .filter(db.Token.token == token)
            .first()
        )
        if db_token is None:
            raise HTTPException(
                status_code=401, detail='Invalid token', headers=HEADERS
            )
        user = db_token.user
        stocks: List[Tuple[db.Portfolio, db.Stock]] = (
            manager.session.query(db.Portfolio, db.Stock)
            .join(db.Stock)
            .filter(db.Portfolio.user_id == user.id)
            .all()
        )
        for p, s in stocks:
            user_stocks.update({s.shortname: p})

    stock_info: db.Stock = (
        manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    )
    if stock_info is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Stock not found',
            headers=HEADERS,
        )

    market_data = await moex_client.actual_individual(stock_info.shortname)
    price = market_data[12]
    change = market_data[25]
    deals = market_data[54]

    stock = Stock(
        id=stock_info.id,
        fullname=stock_info.fullname,
        shortname=stock_info.shortname,
        currency=stock_info.currency,
        price=price,
        change=change,
        volume_of_deals=deals,
    )

    if stock_info.shortname in user_stocks:
        stock.owned = True
        _p = user_stocks[stock_info.shortname]
        stock.quantity = _p.quantity
        stock.profit = _p.quantity * price - _p.spent

    if h:
        prev_history = moex_cache.get_history(stock_info.id)
        if prev_history is not None:
            if prev_history.updated.date() == datetime.date.today():
                stock.history = prev_history.data
                return Response(content=stock.json(), headers=HEADERS)

            start_from_date = (
                prev_history.last_date + datetime.timedelta(days=1)
            ).isoformat()
            small_history = prev_history.data
            backet_size = 3
        else:
            start_from_date = '1990-01-01'
            small_history = []
            backet_size = 10

        today = datetime.date.today().strftime(r'%Y-%m-%d')
        history = await moex_client.history(
            stock_info.shortname, start_from_date, today, backet_size
        )
        for h in history:
            if h[11] is not None or ALLOW_HISTORY_NONE:
                small_history.append([h[1], h[11]])

        moex_cache[stock_info.shortname] = small_history
        moex_cache.save()

        stock.history = small_history

    return Response(content=stock.json(), headers=HEADERS)


@app.post('/stocks/add/{id}', status_code=status.HTTP_200_OK)
async def add_stock_handler(
    request: Request, id: int, quantity: int = Body(..., embed=True)
) -> Any:
    token: str = request.headers.get('Authorization', None)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization requied',
            headers=HEADERS,
        )

    db_token = (
        manager.session.query(db.Token).filter(db.Token.token == token).first()
    )

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
            headers=HEADERS,
        )

    user = db_token.user

    stock: db.Stock = (
        manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    )

    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Stock not found',
            headers=HEADERS,
        )

    stock_info = await moex_client.actual_individual(stock.shortname)
    price = float(stock_info[12])

    portfolio: db.Portfolio = (
        manager.session.query(db.Portfolio)
        .filter(
            (db.Portfolio.user_id == user.id) & (db.Portfolio.stock_id == id)
        )
        .first()
    )

    if portfolio is None:
        portfolio = db.Portfolio(user=user, stock=stock, spent=0.0)
        delta = quantity
    else:
        delta = quantity - portfolio.quantity

    portfolio.quantity = quantity
    portfolio.spent += price * delta

    manager.session.commit()

    return JSONResponse(content={'detail': 'ok'}, headers=HEADERS)


@app.delete('/stocks/{id}', status_code=status.HTTP_200_OK)
async def remove_stock_handler(
    request: Request, id: int, user: db.User = Depends(strict_auth)
) -> Any:

    stock: db.Stock = (
        manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    )

    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Stock not found',
            headers=HEADERS,
        )

    portfolio: db.Portfolio = (
        manager.session.query(db.Portfolio)
        .filter(
            (db.Portfolio.user_id == user.id) & (db.Portfolio.stock_id == id)
        )
        .first()
    )

    if portfolio is not None:
        manager.session.delete(portfolio)
        manager.session.commit()

    return Response(headers=HEADERS)


@app.get(
    '/predict/{id}', status_code=status.HTTP_200_OK, response_model=Methods
)
async def predict_handler(id: int) -> Any:
    stock_info: db.Stock = (
        manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    )

    if stock_info is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Stock not found',
            headers=HEADERS,
        )

    history: History
    history_exists = False

    prev_history = moex_cache[stock_info.shortname]
    if prev_history is not None:
        if (
            prev_history.updated.date() == datetime.date.today()
        ):  # already exists
            history = History(
                ticker=stock_info.shortname, history=prev_history.data
            )
            history_exists = True

        start_from_date = (
            prev_history.last_date + datetime.timedelta(days=1)
        ).isoformat()
        small_history = prev_history.data
        backet_size = 3
    else:
        start_from_date = '1990-01-01'
        small_history = []
        backet_size = 10

    if not history_exists:
        today = datetime.date.today().strftime(r'%Y-%m-%d')
        hist = await moex_client.history(
            stock_info.shortname, start_from_date, today, backet_size
        )
        for h in hist:
            small_history.append([h[1], h[11]])

        moex_cache[stock_info.shortname] = small_history
        moex_cache.save()

        history = History(ticker=stock_info.shortname, history=small_history)

    methods = []

    for m in PREDICTION_METHODS:
        try:
            p = m(history=history)
            methods.append(p)
        except Exception:
            logger.warning('error in prediction method %s', m.__name__)

    return Response(Methods(methods=methods).json(), headers=HEADERS)
