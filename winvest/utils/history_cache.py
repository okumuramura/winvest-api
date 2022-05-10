import datetime
import os
import pickle
from typing import Optional, Union

import redis

from winvest.models.response_model import History

REDIS_HOST: str = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT: int = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASS: Optional[str] = os.environ.get('REDIS_PASS', None)


class HistoryCache:
    class Cache:
        def __init__(
            self, value: Union[History, float], updated: datetime.datetime
        ) -> None:
            self.value = value
            self.updated = updated

    def __init__(
        self,
        history_expire: datetime.timedelta = datetime.timedelta(hours=1),
        price_expirte: datetime.timedelta = datetime.timedelta(minutes=1),
    ) -> None:
        self.redis = redis.StrictRedis(REDIS_HOST, REDIS_PORT, 0, REDIS_PASS)
        self.history_expire = history_expire
        self.price_expire = price_expirte

    def get_history(self, stock_id: int) -> Optional[Cache]:
        raw_data = self.redis.get(f'stock_{stock_id}_history')
        updated = self.redis.get(f'stock_{stock_id}_history_updated')
        if raw_data is None:
            return None

        updated_date = datetime.datetime.fromisoformat(updated.decode('utf-8'))
        history_data = pickle.loads(raw_data)
        return HistoryCache.Cache(history_data, updated_date)

    def save_history(self, stock_id: int, history: History) -> None:
        history_data = pickle.dumps(history)
        current_date = datetime.datetime.now().isoformat()
        self.redis.set(
            f'stock_{stock_id}_history', history_data, ex=self.history_expire
        )
        self.redis.set(
            f'stock_{stock_id}_history_updated',
            current_date,
            ex=self.history_expire,
        )

    def get_price(self, stock_id: int) -> Optional[Cache]:
        price = self.redis.get(f'stock_{stock_id}_price')
        updated = self.redis.get(f'stock_{stock_id}_price_updated')
        if price is None:
            return None
        numeric_price = float(price)
        updated_date = datetime.datetime.fromisoformat(updated.decode('utf-8'))
        return HistoryCache.Cache(numeric_price, updated_date)

    def save_price(self, stock_id: int, price: str) -> None:
        current_date = datetime.datetime.now().isoformat()
        self.redis.set(f'stock_{stock_id}_price', price, ex=self.price_expire)
        self.redis.set(
            f'stock_{stock_id}_price_updated',
            current_date,
            ex=self.price_expire,
        )
