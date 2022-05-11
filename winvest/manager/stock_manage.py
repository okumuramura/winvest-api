from typing import Optional, List

from sqlalchemy.orm import Session

from winvest import moex_cache, moex_client
from winvest.manager import orm_function, async_orm_function, portfolio_manage
from winvest.models import db, response_model


@async_orm_function
async def load_price(
    stock: db.Stock, session: Session = None
) -> Optional[response_model.Stock]:
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
        market_data = await load_price(stock, session=session)
        if user:
            owned_data = portfolio_manage.get_stock_data(
                user.id, stock.id, session=session
            )
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
