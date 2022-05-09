from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from winvest.models import db


class Manager:
    def __init__(self, db: str) -> None:
        self.engine = create_engine(db)
        self.session: Session = sessionmaker(self.engine)()
