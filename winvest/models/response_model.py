from typing import List, Optional, Tuple

from pydantic import BaseModel

HistoryType = Tuple[str, Optional[float]]


class History(BaseModel):
    ticker: str
    history: List[HistoryType]
    # history: List[List[Union[str, float]]]


class Stock(BaseModel):
    id: int
    fullname: str
    shortname: str
    currency: str
    price: Optional[float]
    change: Optional[float]
    history: List[HistoryType] = []
    volume_of_deals: Optional[float] = None
    owned: bool = False
    quantity: int = 0
    profit: float = 0.0


class StockList(BaseModel):
    stocks: List[Stock]


class Portfolio(BaseModel):
    username: str
    stocks: List[Stock]
    total_value: float
    total_profit: float


class Method(BaseModel):
    name: str
    type: str
    data: List[float]
    error: float


class Methods(BaseModel):
    methods: List[Method]
