from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from winvest import moex_cache, moex_client
from winvest.manager import async_orm_function, orm_function
from winvest.models import db, response_model


@orm_function
def get_stock_data(
    user_id: int, stock_id: int, session: Session = None
) -> Optional[response_model.StockOwned]:
    portfolio: db.Portfolio = (
        session.query(db.Portfolio)
        .filter(
            (db.Portfolio.user_id == user_id)
            & (db.Portfolio.stock_id == stock_id)
        )
        .options(joinedload(db.Portfolio.stock))
        .first()
    )

    if portfolio is None:
        return response_model.StockOwned(
            id=stock_id, shortname='-', owned=False, quantity=0, spent=0.0
        )

    return response_model.StockOwned(
        id=stock_id,
        shortname=portfolio.stock.shortname,
        owned=True,
        quantity=portfolio.quantity,
        spent=portfolio.spent,
    )


@async_orm_function
async def load_price(stock: db.Stock) -> Optional[response_model.Stock]:
    cached_price = moex_cache.get_price(stock.id)

    if cached_price is None:
        moex_price = await moex_client.actual_individual(stock.shortname)
        moex_cache.save_price(stock.id, moex_price)
    else:
        moex_price = cached_price.value

    return response_model.Stock(
        id=stock.id,
        fullname=stock.fullname,
        shortname=stock.shortname,
        currency=stock.currency,
        price=moex_price.price,
        change=moex_price.change,
        volume_of_deals=moex_price.deals,
    )


@orm_function
def get_by_id(stock_id: int, session: Session = None) -> Optional[db.Stock]:
    return session.query(db.Stock).filter(db.Stock.id == stock_id).first()


@async_orm_function
async def load_list(
    user: Optional[db.User] = None,
    offset: int = 0,
    limit: int = 30,
    session: Session = None,
) -> response_model.StockList:
    stocks_query = session.query(db.Stock)

    total = stocks_query.count()
    stocks: List[db.Stock] = stocks_query.offset(offset).limit(limit).all()

    stock_list = []
    for stock in stocks:
        market_data = await load_price(stock)
        if user:
            owned_data = get_stock_data(user.id, stock.id, session=session)
            market_data.owned = owned_data.owned
            market_data.quantity = owned_data.quantity
            if market_data.price is not None:
                market_data.profit = (
                    market_data.price * owned_data.quantity - owned_data.spent
                )
        stock_list.append(market_data)

    return response_model.StockList(
        stocks=stock_list, total=total, offset=offset
    )
