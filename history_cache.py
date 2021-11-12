import datetime
import pickle
from os.path import exists
from typing import Dict, List, Optional

from models.response_model import HistoryType


class HistoryCache:
    class Cache:
        updated: datetime.datetime
        last_date: datetime.date
        data: List[HistoryType]

        def __repr__(self) -> str:
            return f"Cache<updated: {self.updated}, last date: {self.last_date}, data length: {len(self.data)}>"

    def __init__(self, cache_file: str = None) -> None:
        self.cache_file = cache_file
        self.cache: Dict[str, HistoryCache.Cache]

        if cache_file is not None and exists(cache_file):
            with open(cache_file, "rb") as cf:
                self.cache = pickle.load(cf)
        
        else:
            self.cache = {}

    def __getitem__(self, key: str) -> Optional[Cache]:
        return self.cache.get(key, None)

    def __setitem__(self, key: str, value: List[HistoryType]):
        node = self.cache.get(key, None)
        if node is None:
            node = HistoryCache.Cache()

        node.last_date = datetime.date.fromisoformat(value[-1][0])
        node.data = value
        node.updated = datetime.datetime.now()

        self.cache[key] = node

    def __save(self) -> None:
        if self.cache_file is not None:
            with open(self.cache_file, "wb") as cf:
                pickle.dump(self.cache, cf)

    def save(self) -> None:
        self.__save()
