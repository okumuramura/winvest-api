from __future__ import annotations

import datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import uuid4

import bcrypt
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from winvest import Base


class ActiveTypes(Enum):
    STOCK = 1


class User(Base):
    __tablename__ = 'users'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    login: str = Column(String(20), nullable=False, unique=True)
    password: str = Column(String(20), nullable=False)
    registered: datetime.datetime = Column(DateTime, nullable=False)

    portfolio: List[Portfolio] = relationship(
        'Portfolio', back_populates='user'
    )
    tokens: List[Token] = relationship('Token', back_populates='user')
    operations: List[Operation] = relationship(
        'Operation', back_populates='user'
    )

    def __init__(
        self, login: str, password: str, in_hash: bool = False
    ) -> None:
        self.login = login
        self.registered = datetime.datetime.now()
        if in_hash:
            self.password = password
        else:
            self.password = bcrypt.hashpw(
                password.encode('utf-8'), bcrypt.gensalt(10)
            ).decode('utf-8')

    def __repr__(self) -> str:
        return f'User_{self.id}<{self.login}, {self.password}>'

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode('utf-8'), self.password.encode('utf-8')
        )


class Portfolio(Base):
    __tablename__ = 'portfolio'

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey('users.id'))
    stock_id: int = Column(Integer, ForeignKey('stocks.id'))
    quantity: int = Column(Integer, default=0)
    spent: float = Column(Float, default=0.0)

    user: User = relationship('User', back_populates='portfolio')
    stock: Stock = relationship('Stock', back_populates='portfolio')

    __table_args__ = (
        UniqueConstraint('user_id', 'stock_id', name='_portfolio_unique'),
    )

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
        self,
        short: str,
        full: str,
        _type: ActiveTypes = ActiveTypes.STOCK,
        currency: str = 'rub',
    ) -> None:
        self.shortname = short
        self.fullname = full
        self.type_id = _type.value
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
        if isinstance(user, User):
            self.user = user
        else:
            self.user_id = user
        self.token = str(uuid4())
        self.created = datetime.datetime.now()

    def __repr__(self) -> str:
        return f'Token_{self.id}<{self.token, self.user_id}>'


class Operation(Base):
    __tablename__ = 'operations'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    type: str = Column(String(20), nullable=False)
    user_id: int = Column(Integer, ForeignKey('users.id'))
    subject_id: Optional[int] = Column(
        Integer, ForeignKey('stocks.id'), nullable=True, default=None
    )
    date: datetime.datetime = Column(DateTime, nullable=False)
    args: Optional[str] = Column(String(200), nullable=True)

    user: User = relationship('User', back_populates='operations')
    subject: Optional[Stock] = relationship('Stock')

    def __init__(
        self,
        user_id: int,
        _type: str,
        subject: Optional[int] = None,
        args: Optional[str] = None,
    ) -> None:
        self.user_id = user_id
        self.type = _type
        self.subject_id = subject
        self.args = args
        self.date = datetime.datetime.now()

    def __repr__(self) -> str:
        return f'Operation_{self.id}<{self.user_id}, {self.type}, {self.subject_id}>'
