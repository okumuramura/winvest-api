import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from winvest.utils.moex_api import AsyncClient
from winvest.utils.history_cache import HistoryCache

DB = 'sqlite:///database.db'

logger = logging.Logger(__name__)

Base = declarative_base()
engine = create_engine(DB)
Session = sessionmaker(engine, expire_on_commit=False)

moex_client = AsyncClient()
moex_cache = HistoryCache()
