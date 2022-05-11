from typing import List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from winvest import moex_client
from winvest.manager import (
    async_orm_function,
    create_operation,
    orm_function,
    stock_manage,
)
from winvest.models import db, response_model


@async_orm_function
async def get_by_user(
    user_id: int, offset: int = 0, limit: int = 20, session: Session = None
) -> response_model.Portfolio:
    tickers_query = (
        session.query(db.Portfolio, db.Stock)
        .join(db.Stock)
        .filter(db.Portfolio.user_id == user_id)
    )

    total = tickers_query.count()
    tickers: List[Tuple[db.Portfolio, db.Stock]] = (
        tickers_query.offset(offset).limit(limit).all()
    )

    market = await moex_client.actual()

    data = []
    total_value = 0.0
    total_profit = 0.0

    market_stocks = {x[0]: (x[12], x[25], x[54]) for x in market}

    for portfolio, stock in tickers:
        data.append(market_stocks.get(stock.shortname, (None, None, None)))

    stock_list: List[response_model.Stock] = []

    for (portfolio, stock), data_row in zip(tickers, data):
        stock_model = response_model.Stock(
            id=stock.id,
            fullname=stock.fullname,
            shortname=stock.shortname,
            currency=stock.currency,
            price=data_row[0],
            change=data_row[1],
            volume_of_deals=data_row[2],
            owned=True,
            quantity=portfolio.quantity,
        )
        value = (
            0
            if data_row[0] is None
            else float(data_row[0]) * portfolio.quantity
        )
        stock_model.profit = value - portfolio.spent
        total_value += value
        total_profit += stock_model.profit
        stock_list.append(stock_model)

    stock_list = sorted(
        stock_list,
        key=lambda x: 0 if x.volume_of_deals is None else x.volume_of_deals,
        reverse=True,
    )

    return response_model.Portfolio(
        username='?',
        stocks=stock_list,
        total=total,
        offset=offset,
        total_value=total_value,
        total_profit=total_profit,
    )


@async_orm_function
async def add_stock(
    user: db.User, stock: db.Stock, quantity: int, session: Session = None
) -> Optional[db.Portfolio]:
    portfolio: db.Portfolio = (
        session.query(db.Portfolio)
        .filter(
            (db.Portfolio.user_id == user.id)
            & (db.Portfolio.stock_id == stock.id)
        )
        .first()
    )

    if not portfolio:
        portfolio = db.Portfolio(user_id=user.id, stock_id=stock.id)
        session.add(portfolio)

    price = await stock_manage.load_price(stock)
    if price.price is None:
        return None

    delta = quantity - portfolio.quantity
    portfolio.quantity = quantity
    portfolio.spent += price.price * delta

    args = {'quantity': quantity, 'by_price': price.price}

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return None

    create_operation(user.id, 'ADD', stock, str(args), session=session)

    return portfolio


@orm_function
def remove_stock(user: db.User, stock_id: int, session: Session = None) -> bool:
    portfolio = (
        session.query(db.Portfolio)
        .filter(
            (db.Portfolio.user_id == user.id)
            & (db.Portfolio.stock_id == stock_id)
        )
        .delete()
    )

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return False
    return bool(portfolio)
