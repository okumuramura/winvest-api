import asyncio
import base64
from http import HTTPStatus

import aiohttp
import requests

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


class Client:
    def __init__(self):
        self.session = requests.Session()

    def auth(self, user: str, password: str) -> HTTPStatus:
        auth_data = (user + ':' + password).encode('utf-8')
        response = self.session.get(
            urls['auth'],
            headers={
                'Authorization': 'Basic %s' % base64.b64encode(auth_data)[:-1]
            },
        )
        return HTTPStatus(response.status_code)

    def history(self, security: str, _from: str, _till: str):
        args = {
            'engine': 'stock',
            'market': 'shares',
            'board': 'tqbr',
            # 'board': 'eqvl',
            'security': security,
            'from': _from,
            'till': _till,
        }

        data = []
        data_len = -1
        start = 0

        while data_len != 0:
            print((urls['history'] % args) + '&start=' + str(start))
            response = self.session.get(
                (urls['history'] % args) + '&start=' + str(start)
            )
            print(response.status_code)
            # print(response.json())
            if response.status_code == HTTPStatus.OK:
                d = response.json()['history']['data']
                data_len = len(d)
                data.extend(d)
                start += data_len
            else:
                raise Exception('NOOOOOOO')

        return data

    def actual(self, board: str = 'tqbr'):
        args = {'engine': 'stock', 'market': 'shares', 'board': board}

        response = self.session.get(urls['actual'] % args)

        return response.json()['marketdata']['data']

    def actual_individual(self, symbol: str, board: str = 'tqbr'):
        args = {
            'engine': 'stock',
            'market': 'shares',
            'board': board,
            'symbol': symbol,
        }
        print(urls['actual_indi'] % args)
        response = self.session.get(urls['actual_indi'] % args)

        return response.json()['marketdata']['data'][0]


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
