import datetime

from winvest import ALLOW_HISTORY_NONE, moex_cache, moex_client
from winvest.models import db, response_model


async def load_up(stock: db.Stock) -> response_model.History:
    previous_history = moex_cache.get_history(stock.id)
    if previous_history is not None:
        if previous_history.updated.date() == datetime.date.today():
            return previous_history.value

        last_date: datetime.datetime = previous_history.value[-1][0]
        start_from_date = (
            last_date.date() + datetime.timedelta(days=1)
        ).isoformat()
        cached_history = previous_history.value.history
        backet_size = 3
    else:
        start_from_date = '1999-01-01'
        cached_history = []
        backet_size = 10

    today = datetime.date.today().isoformat()
    history = await moex_client.history(
        stock.shortname, start_from_date, today, backet_size=backet_size
    )

    for history_row in history:
        if history_row[11] is not None or ALLOW_HISTORY_NONE:
            cached_history.append((history_row[1], history_row[11]))

    history_model = response_model.History(
        ticker=stock.shortname, history=cached_history
    )
    moex_cache.save_history(stock.id, history_model)

    return history_model
