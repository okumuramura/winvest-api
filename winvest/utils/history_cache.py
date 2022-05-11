import datetime
import os
import pickle
from typing import Optional, Union

import redis

from winvest.models.response_model import History, Methods
from winvest.utils.moex_api import MOEXStock

REDIS_HOST: str = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT: int = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASS: Optional[str] = os.environ.get('REDIS_PASS', None)


class HistoryCache:
    class Cache:
        def __init__(
            self,
            value: Union[History, MOEXStock, Methods],
            updated: datetime.datetime,
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
            f'stock_{stock_id}_history', history_data
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
        price_data = pickle.loads(price)
        updated_date = datetime.datetime.fromisoformat(updated.decode('utf-8'))
        return HistoryCache.Cache(price_data, updated_date)

    def save_price(self, stock_id: int, price: MOEXStock) -> None:
        current_date = datetime.datetime.now().isoformat()
        price_data = pickle.dumps(price)
        self.redis.set(
            f'stock_{stock_id}_price', price_data, ex=self.price_expire
        )
        self.redis.set(
            f'stock_{stock_id}_price_updated',
            current_date,
            ex=self.price_expire,
        )

    def get_predictions(self, stock_id: int) -> Optional[Cache]:
        raw_predictions = self.redis.get(f'stock_{stock_id}_predictions')
        updated = self.redis.get(f'stock_{stock_id}_predictions_updated')
        if raw_predictions is None:
            return None
        predictions = pickle.loads(raw_predictions)
        updated_date = datetime.datetime.fromisoformat(updated.decode('utf-8'))
        return HistoryCache.Cache(predictions, updated_date)

    def save_predisctions(self, stock_id: int, predictions: Methods) -> None:
        current_date = datetime.datetime.now().isoformat()
        predictions_data = pickle.dumps(predictions)
        self.redis.set(
            f'stock_{stock_id}_predictions',
            predictions_data,
            ex=self.history_expire,
        )
        self.redis.set(
            f'stock_{stock_id}_predictions_updated',
            current_date,
            ex=self.history_expire,
        )
