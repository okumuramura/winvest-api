from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Manager:
    def __init__(self, database: str) -> None:
        self.engine = create_engine(database)
        self.session: Session = sessionmaker(self.engine)()
