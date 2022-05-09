from __future__ import annotations

import datetime
from typing import List, Union
from uuid import uuid4
import bcrypt

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ActiveTypes:
    STOCK = 0


class User(Base):
    __tablename__ = 'users'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    login: str = Column(String(20), nullable=False, unique=True)
    password: str = Column(String(20), nullable=False)

    portfolio: List[Portfolio] = relationship(
        'Portfolio', back_populates='user'
    )
    tokens: List[Token] = relationship('Token', back_populates='user')

    def __init__(self, login: str, password: str, in_hash=True) -> None:
        self.login = login
        self.password = password

    def __repr__(self) -> str:
        return f'User_{self.id}<{self.login}, {self.password}>'

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password)


class Portfolio(Base):
    __tablename__ = 'portfolio'

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey('users.id'))
    stock_id: int = Column(Integer, ForeignKey('stocks.id'))
    quantity: int = Column(Integer, default=0)
    spent: float = Column(Float, default=0.0)

    user: List[User] = relationship('User', back_populates='portfolio')
    stock: List[Stock] = relationship('Stock', back_populates='portfolio')

    def __repr__(self) -> str:
        return f'Portfolio<{self.user_id}, {self.stock_id}, {self.quantity}>'


class Stock(Base):
    __tablename__ = 'stocks'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    shortname: str = Column(String(10))
    fullname: str = Column(String(200))
    requests: int = Column(Integer, default=0)
    currency: str = Column(String(3), default='rub')
    type_id: int = Column(Integer, ForeignKey('activetypes.id'))

    portfolio: List[Portfolio] = relationship(
        'Portfolio', back_populates='stock'
    )

    def __init__(
        self, short: str, full: str, type: int = 0, currency: str = 'rub'
    ) -> None:
        self.shortname = short
        self.fullname = full
        self.type_id = type + 1  # with autoincrement
        self.currency = currency

    def __repr__(self) -> str:
        return f'Stock_{self.id}<{self.shortname}, {self.fullname}>'


class ActiveType(Base):
    __tablename__ = 'activetypes'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    typename: str = Column(String(25))

    def __init__(self, typename: str) -> None:
        self.typename = typename

    def __repr__(self) -> str:
        return f'ActiveType_{self.id}<{self.typename}>'


class Token(Base):
    __tablename__ = 'tokens'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    token: str = Column(String(60), unique=True)
    created: datetime.datetime = Column(DateTime)
    user_id: int = Column(Integer, ForeignKey('users.id'))

    user: User = relationship('User', back_populates='tokens')

    def __init__(self, user: Union[User, int]) -> None:
        if type(user) == User:
            self.user = User
        else:
            self.user_id = user
        self.token = str(uuid4())
        self.created = datetime.datetime.now()

    def __repr__(self) -> str:
        return f'Token_{self.id}<{self.token, self.user_id}>'
