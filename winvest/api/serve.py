import datetime
from typing import Any, Dict, List, Tuple
from http import HTTPStatus

import bcrypt
from fastapi import Body, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from winvest.api import logger
from winvest.api.manager import Manager
from winvest.models import db
from winvest.models.request_models import User
from winvest.models.response_model import (
    History,
    Methods,
    Portfolio,
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
from winvest.utils.history_cache import HistoryCache
from winvest.utils.moex_api import AsyncClient

app = FastAPI()
# cli = Client()
moex_client = AsyncClient()
manager = Manager('sqlite:///database.db')
cache = HistoryCache('./cache')

HEADERS = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, PATCH, DELETE',
    'Access-Control-Allow-Headers': 'X-Requested-With,content-type',
    'Access-Control-Allow-Origin': '*',
}

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

ALLOW_HISTORY_NONE = False


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
                status_code=HTTPStatus.UNAUTHORIZED, detail='Invalid token', headers=HEADERS
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
            status_code=HTTPStatus.NOT_FOUND, detail='Stock not found', headers=HEADERS
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
        prev_history = cache[stock_info.shortname]
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

        cache[stock_info.shortname] = small_history
        cache.save()

        stock.history = small_history

    return Response(content=stock.json(), headers=HEADERS)


@app.get(
    '/history/stocks/{id}',
    status_code=status.HTTP_200_OK,
    response_model=History,
)
async def history_handler(request: Request, id: int) -> Any:
    stock_info: db.Stock = (
        manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    )
    if stock_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Stock not found',
            headers=HEADERS,
        )

    prev_history = cache[stock_info.shortname]
    if prev_history is not None:
        if (
            prev_history.updated.date() == datetime.date.today()
        ):  # already exists
            return Response(
                content=History(
                    ticker=stock_info.shortname, history=prev_history.data
                ).json(),
                headers=HEADERS,
            )

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

    cache[stock_info.shortname] = small_history
    cache.save()

    return Response(
        content=History(
            ticker=stock_info.shortname, history=small_history
        ).json(),
        headers=HEADERS,
    )


@app.post('/register', status_code=status.HTTP_201_CREATED)
async def register_handler(request_user: User) -> Any:
    password_hash = bcrypt.hashpw(request_user.password, bcrypt.gensalt(10))
    user = db.User(request_user.login, password_hash)
    manager.session.add(user)
    try:
        manager.session.commit()
    except IntegrityError:
        manager.session.rollback()
        raise HTTPException(
            status_code=406, detail='Login already exists', headers=HEADERS
        )

    return JSONResponse({'detail': 'ok'}, headers=HEADERS)


@app.post('/login', status_code=status.HTTP_200_OK)
async def login_handler(request_user: User) -> Any:
    user: db.User = (
        manager.session.query(db.User)
        .filter(db.User.login == request_user.login)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=406, detail='User is not found', headers=HEADERS
        )

    if not bcrypt.checkpw(request_user.password, user.password):
        raise HTTPException(
            status_code=406, detail='Wrong password', headers=HEADERS
        )

    token = db.Token(user.id)

    manager.session.add(token)
    manager.session.commit()

    return JSONResponse(content={'token': token.token}, headers=HEADERS)


@app.get('/portfolio', status_code=status.HTTP_200_OK, response_model=Portfolio)
async def portfolio_handler(request: Request) -> Any:

    try:
        token: str = request.headers['Authorization']
    except KeyError:
        raise HTTPException(
            status_code=401, detail='Authorization requied', headers=HEADERS
        )

    db_token = (
        manager.session.query(db.Token).filter(db.Token.token == token).first()
    )

    if db_token is None:
        raise HTTPException(
            status_code=401, detail='Invalid token', headers=HEADERS
        )

    user = db_token.user

    tickers: List[Tuple[db.Portfolio, db.Stock]] = (
        manager.session.query(db.Portfolio, db.Stock)
        .join(db.Stock)
        .filter(db.Portfolio.user_id == user.id)
        .all()
    )

    market = await moex_client.actual()

    data = []
    total_value = 0
    total_profit = 0

    market_stocks = {s[0]: (s[12], s[25], s[54]) for s in market}

    for p, s in tickers:
        data.append(market_stocks.get(s.shortname, (None, None)))

    stocks_list = []

    for (p, s), d in zip(tickers, data):

        stock = Stock(
            id=s.id,
            fullname=s.fullname,
            shortname=s.shortname,
            currency=s.currency,
            price=d[0],
            change=d[1],
            volume_of_deals=d[2],
            owned=True,
            quantity=p.quantity,
        )
        value = 0 if d[0] is None else float(d[0]) * p.quantity
        stock.profit = value - p.spent
        total_value += value
        total_profit += stock.profit
        stocks_list.append(stock)

    stocks_list = sorted(
        stocks_list,
        key=lambda x: 0 if x.volume_of_deals is None else x.volume_of_deals,
        reverse=True,
    )

    return Response(
        content=Portfolio(
            stocks=stocks_list,
            total_value=total_value,
            username=user.login,
            total_profit=total_profit,
        ).json(),
        headers=HEADERS,
    )


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


@app.post('/stocks/remove/{id}', status_code=status.HTTP_200_OK)
async def remove_stock_handler(request: Request, id: int) -> Any:
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
            status_code=HTTPStatus.NOT_FOUND, detail='Stock not found', headers=HEADERS
        )

    history: History
    history_exists = False

    prev_history = cache[stock_info.shortname]
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

        cache[stock_info.shortname] = small_history
        cache.save()

        history = History(ticker=stock_info.shortname, history=small_history)

    methods = []

    for m in PREDICTION_METHODS:
        try:
            p = m(history=history)
            methods.append(p)
        except Exception as error:
            logger.warning('error in prediction method %s', m.__name__)

    return Response(Methods(methods=methods).json(), headers=HEADERS)
