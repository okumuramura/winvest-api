from typing import Optional
import asyncio

from pydantic import BaseModel
import aiohttp

urls = {
    'history': (
        'https://iss.moex.com/iss/history'
        '/engines/%(engine)s/markets/%(market)s'
        '/securities/%(security)s.json?from=%(from)s&till=%(till)s'
    ),
    'auth': 'https://passport.moex.com/authenticate',
    'actual': (
        'https://iss.moex.com/iss/engines/'
        '%(engine)s/markets/%(market)s'
        '/boards/%(board)s/securities.json'
    ),
    'actual_indi': (
        'https://iss.moex.com/iss/engines'
        '/%(engine)s/markets/%(market)s'
        '/boards/%(board)s/securities/%(symbol)s.json'
    ),
}

BOARD_WHITE_LIST = ['TQBR', 'EQVL']


class MOEXStock(BaseModel):
    ticker: str
    price: Optional[float]
    change: Optional[float]
    deals: Optional[float]


class AsyncClient:
    async def __history_part(
        self,
        session: aiohttp.ClientSession,
        security: str,
        _from: str,
        _till: str,
        start: int,
    ):
        args = {
            'engine': 'stock',
            'market': 'shares',
            # 'board': 'tqbr',
            'board': 'eqlv',
            'security': security,
            'from': _from,
            'till': _till,
        }
        url = urls['history'] % args + '&start=' + str(start)
        async with session.get(url) as resp:
            data = await resp.json()

            return data['history']['data']

    async def history(
        self, security: str, _from: str, _till: str, backet_size: int = 10
    ):

        need_more = True
        start = 0
        data = []
        while need_more:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    asyncio.ensure_future(
                        self.__history_part(session, security, _from, _till, s)
                    )
                    for s in range(start, start + backet_size * 100 + 1, 100)
                ]
                history_data = await asyncio.gather(*tasks)

                for d in history_data:
                    if len(d) > 0:
                        data.extend(d)
                    else:
                        need_more = False
                        break
                start += backet_size * 100

        return data

    async def actual(self, board: str = 'tqbr'):
        args = {'engine': 'stock', 'market': 'shares', 'board': board}

        async with aiohttp.ClientSession() as session:
            async with session.get(urls['actual'] % args) as resp:
                data = await resp.json()
                return data['marketdata']['data']

    async def actual_individual(
        self, symbol: str, board: str = 'tqbr'
    ) -> MOEXStock:
        args = {
            'engine': 'stock',
            'market': 'shares',
            'board': board,
            'symbol': symbol,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(urls['actual_indi'] % args) as resp:
                data = await resp.json()
                stock_info = data['marketdata']['data'][0]
                ticker = stock_info[0]
                price = stock_info[12]
                change = stock_info[25]
                deals = stock_info[54]
                return MOEXStock(
                    ticker=ticker, price=price, change=change, deals=deals
                )
