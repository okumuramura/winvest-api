from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, Table, Time, create_engine, Float)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

Base = declarative_base()

class ActiveTypes:
    STOCK = 0

class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    login: str = Column(String(20), nullable=False, unique=True)
    password: str = Column(String(20), nullable=False)

    portfolio: List[Portfolio] = relationship("Portfolio", back_populates="user")
    tokens: List[Token] = relationship("Token", back_populates="user")

    def __init__(self, login: str, password: str, in_hash = True) -> None:
        self.login = login
        self.password = password

    def __repr__(self) -> str:
        return f"User_{self.id}<{self.login}, {self.password}>"

    def add_stocks(self, stocks: Dict[Union[int, Stock], int]) -> None:
        for stock, quantity in stocks.items():
            p = Portfolio()
            p.quantity = quantity
            if type(stock) == int:
                p.stock_id = stock
            elif type(stock) == Stock:
                p.stock = stock

            self.portfolio.append(p)


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"))
    stock_id: int = Column(Integer, ForeignKey("stocks.id"))
    quantity: int = Column(Integer, default=0)
    spent: float = Column(Float, default=0.0)

    user: List[User] = relationship("User", back_populates="portfolio")
    stock: List[Stock] = relationship("Stock", back_populates="portfolio")

    def __repr__(self) -> str:
        return f"Portfolio<{self.user_id}, {self.stock_id}, {self.quantity}>"

class Stock(Base):
    __tablename__ = "stocks"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    shortname: str = Column(String(10))
    fullname: str = Column(String(200))
    requests: int = Column(Integer, default=0)
    currency: str = Column(String(3), default="rub")
    type_id: id = Column(Integer, ForeignKey("activetypes.id"))

    portfolio: List[Portfolio] = relationship("Portfolio", back_populates="stock")

    def __init__(self, short: str, full: str, type: int = 0, currency: str = "rub") -> None:
        self.shortname = short
        self.fullname = full
        self.type_id = type + 1 # with autoincrement
        self.currency = currency

    def __repr__(self) -> str:
        return f"Stock_{self.id}<{self.shortname}, {self.fullname}>"

class ActiveType(Base):
    __tablename__ = "activetypes"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    typename: str = Column(String(25))

    def __init__(self, typename: str) -> None:
        self.typename = typename

    def __repr__(self) -> str:
        return f"ActiveType_{self.id}<{self.typename}>"

class Token(Base):
    __tablename__ = "tokens"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    token: str = Column(String(60), unique=True)
    created: datetime.datetime = Column(DateTime)
    user_id: int = Column(Integer, ForeignKey("users.id"))

    user: User = relationship("User", back_populates="tokens")

    def __init__(self, user: Union[User, int]) -> None:
        if type(user) == User:
            self.user = User
        else:
            self.user_id = user
        self.token = str(uuid4())
        self.created = datetime.datetime.now()

    def __repr__(self) -> str:
        return f"Token_{self.id}<{self.token, self.user_id}>"

if __name__ == "__main__":
    import os
    os.remove("./database.db")

    engine = create_engine("sqlite:///database.db", echo = False, encoding = "utf-8")
    Base.metadata.create_all(engine)
    session = Session(bind = engine)

    # test_users = [
    #     User("test_user", "rhy3fqjkfkuh"),
    #     User("mura", "jkhfiuiwajfa"),
    #     User("eve", "jkahsdkjahskdjw")
    # ]

    TYPES = "Облигации,Акции,Депозитарные расписки,Инвестиционные паи,Акции иностранного фонда,Еврооблигации,Ипотечные сертификаты участия"
    test_types = [ActiveType(tp) for tp in TYPES.split(",")]

    # test_stocks = [
    #     Stock("AAPL", "Apple", ActiveTypes.STOCK),
    #     Stock("MSFT", "Microsoft", ActiveTypes.STOCK)
    # ]

    # session.add_all(test_users)
    session.add_all(test_types)
    #session.add_all(test_stocks)

    session.commit()

    # uesrs = session.query(User).all()
    # stocks = session.query(Stock).all()
    # t_user, mura, eve = uesrs
    # apple, msft = stocks

    # p = Portfolio()
    # p.quantity = 4
    # p.stock = apple
    # mura.portfolio.append(p)

    # eve.add_stocks({
    #     apple: 10,
    #     msft: 20,
    #     Stock("GOOG", "Alphabet", ActiveTypes.STOCK): 2
    # })

    # session.commit()
