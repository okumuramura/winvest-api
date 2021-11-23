import asyncio
import datetime
import time
from typing import Dict, List, Tuple

import bcrypt
from fastapi import (Body, FastAPI, Header, HTTPException, Request, Response,
                     status)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

import db
from history_cache import HistoryCache
from manager import Manager
from models.request_models import User
from models.response_model import History, Method, Methods, Stock, StockList, Portfolio
from moex_api import AsyncClient, Client
from predictions.basic import (exponential_approximation, linear_approximation,
                               logarithmic_approximation,
                               quadratic_approximation,
                               holt_win_fcast)

app = FastAPI()
#cli = Client()
cli = AsyncClient()
manager = Manager("sqlite:///database.db")
cache = HistoryCache("./cache")

HEADERS = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, PATCH, DELETE",
    "Access-Control-Allow-Headers": "X-Requested-With,content-type",
    "Access-Control-Allow-Origin": "*"
}   

PREDICTION_METHODS = [
    linear_approximation,
    quadratic_approximation,
    logarithmic_approximation,
    exponential_approximation,
    holt_win_fcast
]

@app.get("/stocks", status_code=status.HTTP_200_OK, response_model=StockList)
async def stocks_handler(request: Request):
    token = request.headers.get("Authorization", None)
    users_stocks = {}
    if token is not None:
        db_token = manager.session.query(db.Token).filter(db.Token.token == token).first()
        if db_token is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db_token.user
        stocks: List[Tuple[db.Portfolio, db.Stock]] = (manager.session.query(db.Portfolio, db.Stock)
                                .join(db.Stock).filter(db.Portfolio.user_id == user.id).all())
        for p, s in stocks:
            users_stocks.update({s.shortname: p.quantity})

    api_stocks_list = await cli.actual()
    stocks_list = []
    for s in api_stocks_list:
        short = s[0]
        price = s[12]
        change = s[25]
        stock_info = manager.session.query(db.Stock).filter(db.Stock.shortname == short).first()
        if stock_info is not None:
            stock = Stock(
                id = stock_info.id,
                fullname = stock_info.fullname,
                shortname = stock_info.shortname,
                currency = stock_info.currency,
                price = price,
                change = change
            )
            if stock_info.shortname in users_stocks:
                stock.owned = True
                stock.quantity = users_stocks[stock_info.shortname]
            stocks_list.append(stock)
        else:
            print("NOT IN DB:", short, price)

    return Response(content=StockList(stocks = stocks_list).json(), headers=HEADERS)

@app.get("/stocks/{id}", status_code=status.HTTP_200_OK, response_model=Stock)
async def stock_handler(request: Request, id: int, h: bool = False):
    token = request.headers.get("Authorization", None)
    user_stocks = {}
    if token is not None:
        db_token = manager.session.query(db.Token).filter(db.Token.token == token).first()
        if db_token is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db_token.user
        stocks: List[Tuple[db.Portfolio, db.Stock]] = (manager.session.query(db.Portfolio, db.Stock)
                                .join(db.Stock).filter(db.Portfolio.user_id == user.id).all())
        for p, s in stocks:
            user_stocks.update({s.shortname: p.quantity})

    stock_info = manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    if stock_info is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    market_data = await cli.actual_individual(stock_info.shortname)
    price = market_data[12]
    change = market_data[25]

    stock = Stock(
        id = stock_info.id,
        fullname = stock_info.fullname,
        shortname = stock_info.shortname,
        currency = stock_info.currency,
        price = price,
        change = change
    )

    if stock_info.shortname in user_stocks:
        stock.owned = True
        stock.quantity = user_stocks[stock_info.shortname]

    if h:  
        prev_history = cache[stock_info.shortname]
        if prev_history is not None:
            if prev_history.updated.date() == datetime.date.today():
                stock.history = prev_history.data
                return Response(content = stock.json(), headers=HEADERS)

            start_from_date = (prev_history.last_date + datetime.timedelta(days=1)).isoformat()
            small_history = prev_history.data
            backet_size = 3
        else:
            start_from_date = "1990-01-01"
            small_history = []
            backet_size = 10

        today = datetime.date.today().strftime(r"%Y-%m-%d")
        history = await cli.history(stock_info.shortname, start_from_date, today, backet_size)
        for h in history:
            small_history.append([h[1], h[11]])

        stock.history = small_history

    return Response(content=stock.json(), headers=HEADERS)

@app.get("/history/stocks/{id}", status_code=status.HTTP_200_OK, response_model=History)
async def history_handler(request: Request, id: int):
    stock_info = manager.session.query(db.Stock).filter(db.Stock.id == id).first()
    if stock_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    prev_history = cache[stock_info.shortname]
    if prev_history is not None:
        if prev_history.updated.date() == datetime.date.today(): # already exists
            return Response(
                content=History(
                    ticker = stock_info.shortname,
                    history = prev_history.data
                ).json(),
                headers=HEADERS
            )

        start_from_date = (prev_history.last_date + datetime.timedelta(days=1)).isoformat()
        small_history = prev_history.data
        backet_size = 3
    else:
        start_from_date = "1990-01-01"
        small_history = []
        backet_size = 10

    today = datetime.date.today().strftime(r"%Y-%m-%d")
    history = await cli.history(stock_info.shortname, start_from_date, today, backet_size)
    for h in history:
        small_history.append([h[1], h[11]])
    
    cache[stock_info.shortname] = small_history
    cache.save()

    return Response(
        content=History(
            ticker = stock_info.shortname,
            history = small_history
        ).json(),
        headers=HEADERS
    )
    


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_handler(request_user: User):
    password_hash = bcrypt.hashpw(request_user.password, bcrypt.gensalt(10))
    user = db.User(request_user.login, password_hash)
    manager.session.add(user)
    try:
        manager.session.commit()
    except IntegrityError:
        manager.session.rollback()
        raise HTTPException(status_code=406, detail="Login already exists")

    return JSONResponse({"detail": "ok"}, headers=HEADERS)


@app.post("/login", status_code=status.HTTP_200_OK)
async def login_handler(request_user: User):
    user: db.User = manager.session.query(db.User).filter(db.User.login == request_user.login).first()
    if user is None:
        raise HTTPException(status_code=406, detail="User is not found")
    
    if not bcrypt.checkpw(request_user.password, user.password):
        raise HTTPException(status_code=406, detail="Wrong password")
    
    token = db.Token(user.id)

    manager.session.add(token)
    manager.session.commit()

    return JSONResponse(content = {"token": token.token}, headers = HEADERS)

@app.get("/portfolio", status_code=status.HTTP_200_OK, response_model=Portfolio)
async def portfolio_handler(request: Request):

    try:
        token: str = request.headers["Authorization"]
    except KeyError:
        raise HTTPException(status_code=401, detail="Authorization requied")

    db_token = manager.session.query(db.Token).filter(db.Token.token == token).first()

    if db_token is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db_token.user

    tickers: List[Tuple[db.Portfolio, db.Stock]] = (manager.session
                .query(db.Portfolio, db.Stock)
                .join(db.Stock)
                .filter(db.Portfolio.user_id == user.id)
                .order_by(db.Stock.shortname).all()
    )

    market = await cli.actual()

    data = []
    total_value = 0

    actual_stock = 0
    user_stock = tickers[0][1]

    for s in market:
        short = s[0]
        price = s[12]
        change = s[25]

        if user_stock.shortname < short:
            data.append((None, None))
            actual_stock += 1
            if actual_stock == len(tickers):
                break
            user_stock = tickers[actual_stock][1]

        if user_stock.shortname == short:
            data.append((price, change))
            actual_stock += 1
            if actual_stock == len(tickers):
                break
            user_stock = tickers[actual_stock][1]

    stocks_list = []

    for (p, s), d in zip(tickers, data):
        
        stock = Stock(
            id = s.id,
            fullname = s.fullname,
            shortname = s.shortname,
            currency = s.currency,
            price = d[0],
            change = d[1],
            owned = True,
            quantity = p.quantity
        )
        total_value += d[0]
        stocks_list.append(stock)
    
    return Response(
        content=Portfolio(stocks = stocks_list, total_value=total_value).json(),
        headers=HEADERS
    )
    

@app.post("/stocks/add/{id}", status_code=status.HTTP_200_OK)
async def add_stock_handler(request: Request, id: int, quantity: int = Body(...)):
    token: str = request.headers.get("Authorization", None)
    
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization requied")

    db_token = manager.session.query(db.Token).filter(db.Token.token == token).first()

    if db_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db_token.user

    stock: db.Stock = manager.session.query(db.Stock).filter(db.Stock.id == id).first()

    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    portfolio: db.Portfolio = (
        manager.session.query(db.Portfolio)
        .filter((db.Portfolio.user_id == user.id) & (db.Portfolio.stock_id == id))
        .first()
    )

    if portfolio is None:
        portfolio = db.Portfolio(stock = stock)
    
    portfolio.quantity = quantity

    manager.session.commit()

    return JSONResponse(content={"detail": "ok"}, headers=HEADERS)

@app.post("/stocks/remove/{id}", status_code=status.HTTP_200_OK)
async def remove_stock_handler(request: Request, id: int, quantity: int = Body(...)):
    token: str = request.headers.get("Authorization", None)

    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization requied")

    db_token = manager.session.query(db.Token).filter(db.Token.token == token).first()

    if db_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db_token.user

    stock: db.Stock = manager.session.query(db.Stock).filter(db.Stock.id == id).first()

    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    portfolio: db.Portfolio = (
        manager.session.query(db.Portfolio)
        .filter((db.Portfolio.user_id == user.id) & (db.Portfolio.stock_id == id))
        .first()
    )

    if portfolio is not None:
        manager.session.delete(portfolio)
        manager.session.commit()

    return Response(headers=HEADERS)


@app.get("/predict/{id}", status_code=status.HTTP_200_OK, response_model=Methods)
async def predict_handler(request: Request, id: int):
    stock_info = manager.session.query(db.Stock).filter(db.Stock.id == id).first()

    if stock_info is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    history: History
    history_exists = False
    
    prev_history = cache[stock_info.shortname]
    if prev_history is not None:
        if prev_history.updated.date() == datetime.date.today(): # already exists
            history = History(
                ticker = stock_info.shortname,
                history = prev_history.data
            )
            history_exists = True

        start_from_date = (prev_history.last_date + datetime.timedelta(days=1)).isoformat()
        small_history = prev_history.data
        backet_size = 3
    else:
        start_from_date = "1990-01-01"
        small_history = []
        backet_size = 10

    if not history_exists:
        today = datetime.date.today().strftime(r"%Y-%m-%d")
        hist = await cli.history(stock_info.shortname, start_from_date, today, backet_size)
        for h in hist:
            small_history.append([h[1], h[11]])
        
        cache[stock_info.shortname] = small_history
        cache.save()

        history = History(
            ticker = stock_info.shortname,
            history = small_history
        )
    

    methods = []

    for m in PREDICTION_METHODS:
        try:
            p = m(history=history)
            methods.append(p)
        except Exception as error:
            print(str(m), error)

    return Response(
        Methods(
            methods = methods
        ).json(),
        headers=HEADERS
    )