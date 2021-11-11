from typing import List, Dict, Optional, Tuple, Union

from pydantic import BaseModel

HistoryType = Tuple[str, float]

class History(BaseModel):
    ticker: str
    #history: List[HistoryType]
    history: List[List[Union[str, float]]]

class Stock(BaseModel):
    id: int
    fullname: str
    shortname: str
    currency: str
    price: Optional[float]
    change: Optional[float]
    #history: List[HistoryType] = []
    history: List[List[Union[str, float]]] = []
    owned: bool = False
    quantity: int = 0

class StockList(BaseModel):
    stocks: List[Stock]

class Method(BaseModel):
    name: str
    type: str
    data: List[float]
    error: float

class Methods(BaseModel):
    methods: List[Method]
