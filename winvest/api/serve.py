from typing import Any

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

from winvest import moex_client
from winvest.api import (
    HEADERS,
    authorization_route,
    history_route,
    portfolio_route,
    prediction_route,
    stock_route,
    operations_route,
    strict_auth,
)
from winvest.api.manager import Manager
from winvest.models import db

app = FastAPI()
app.include_router(router=authorization_route.router)
app.include_router(router=operations_route.router, prefix='/operations')
app.include_router(router=stock_route.router, prefix='/stocks')
app.include_router(router=history_route.router, prefix='/history')
app.include_router(router=portfolio_route.router, prefix='/portfolio')
app.include_router(router=prediction_route.router, prefix='/predict')

manager = Manager('sqlite:///database.db')

origins = ['http://localhost:3000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)


@app.post('/stocks/add/{id}', status_code=status.HTTP_200_OK)
async def add_stock_handler(
    request: Request,
    id: int,
    quantity: int = Body(..., embed=True),
    user: db.User = Depends(strict_auth),
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
    price = stock_info.price

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
