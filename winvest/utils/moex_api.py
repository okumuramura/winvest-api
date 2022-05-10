import asyncio

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

    async def actual_individual(self, symbol: str, board: str = 'tqbr'):
        args = {
            'engine': 'stock',
            'market': 'shares',
            'board': board,
            'symbol': symbol,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(urls['actual_indi'] % args) as resp:
                data = await resp.json()
                return data['marketdata']['data'][0]
