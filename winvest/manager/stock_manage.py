from typing import Optional

from sqlalchemy.orm import Session

from winvest.manager import orm_function
from winvest.models import db


@orm_function
def get_by_id(stock_id: int, session: Session = None) -> Optional[db.Stock]:
    return session.query(db.Stock).filter(db.Stock.id == stock_id).first()
