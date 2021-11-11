import requests
import asyncio
import aiohttp
from http import HTTPStatus
import base64

urls = {"history": "https://iss.moex.com/iss/history/engines/%(engine)s/markets/%(market)s/boards/%(board)s/securities/%(security)s.json?from=%(from)s&till=%(till)s",
        "auth": "https://passport.moex.com/authenticate",
        "actual": "https://iss.moex.com/iss/engines/%(engine)s/markets/%(market)s/boards/%(board)s/securities.json",
        "actual_indi": "https://iss.moex.com/iss/engines/%(engine)s/markets/%(market)s/boards/%(board)s/securities/%(symbol)s.json"}

class Client:
    def __init__(self):
        self.session = requests.Session()
    
    def auth(self, user: str, password: str) -> HTTPStatus:
        response = self.session.get(
            urls["auth"], 
            headers={
                "Authorization": "Basic %s" %  base64.b64encode((user + ":" + password).encode("utf-8"))[:-1]
            }  
        )
        return HTTPStatus(response.status_code)

    def history(self, security: str, _from: str, _till: str):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": "tqbr",
            #"board": "eqvl",
            "security": security,
            "from": _from,
            "till": _till
        }

        data = []
        l = -1
        start = 0

        while l != 0:
            print((urls["history"] % args) + "&start=" + str(start))
            response = self.session.get((urls["history"] % args) + "&start=" + str(start))
            print(response.status_code)
            #print(response.json())
            if response.status_code == HTTPStatus.OK:
                d = response.json()["history"]["data"]
                l = len(d)
                data.extend(d)
                start += l
            else:
                raise Exception("NOOOOOOO")
        
        return data

    def actual(self, board: str = "tqbr"):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": board
        }

        response = self.session.get(urls["actual"] % args)
        
        return response.json()["marketdata"]["data"]

    def actual_individual(self, symbol: str, board: str = "tqbr"):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": board,
            "symbol": symbol
        }
        print(urls["actual_indi"] % args)
        response = self.session.get(urls["actual_indi"] % args)

        return response.json()["marketdata"]["data"][0]

class AsyncClient:
    async def __history_part(self, session: aiohttp.ClientSession, security: str, _from: str, _till: str, start: int):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": "tqbr",
            #"board": "eqvl",
            "security": security,
            "from": _from,
            "till": _till
        }
        url = urls["history"] % args + "&start=" + str(start)
        async with session.get(url) as resp:
            data = await resp.json()

            return data["history"]["data"]

    async def history(self, security: str, _from: str, _till: str, backet_size: int = 10):

        need_more = True
        start = 0
        data = []
        while need_more:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    asyncio.ensure_future(self.__history_part(session, security, _from, _till, s)) for s in range(start, start + backet_size * 100 + 1, 100)
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

    async def actual(self, board: str = "tqbr"):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": board
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(urls["actual"] % args) as resp:
                data = await resp.json()
                return data["marketdata"]["data"]

    async def actual_individual(self, symbol: str, board: str = "tqbr"):
        args = {
            "engine": "stock",
            "market": "shares",
            "board": board,
            "symbol": symbol
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(urls["actual_indi"] % args) as resp:
                data = await resp.json()
                return data["marketdata"]["data"][0]
            
async def main():
    client = AsyncClient()
    data = await client.history("VTBR", "1990-01-01", "2021-11-10")
    print(data)


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    exit()

    import pandas as pd
    cli = Client()
    #print(*cli.history("VTBR", "2021-11-05", "2021-10-05"), sep = "\n")

    # for c in cli.history("VTBR", "2000-01-01", "2020-01-01"):
    #     print(*c)

    # print(cli.actual())
    d = cli.actual_individual("VTBR")
    print(len(d))
    dt = pd.Series(d)
    c = ["SECID", "BOARDID", "BID", "BIDDEPTH", "OFFER", "OFFERDEPTH", "SPREAD", "BIDDEPTHT", "OFFERDEPTHT", "OPEN", "LOW", "HIGH", "LAST", "LASTCHANGE", "LASTCHANGEPRCNT", "QTY", "VALUE", "VALUE_USD", "WAPRICE", "LASTCNGTOLASTWAPRICE", "WAPTOPREVWAPRICEPRCNT", "WAPTOPREVWAPRICE", "CLOSEPRICE", "MARKETPRICETODAY", "MARKETPRICE", "LASTTOPREVPRICE", "NUMTRADES", "VOLTODAY", "VALTODAY", "VALTODAY_USD", "ETFSETTLEPRICE", "TRADINGSTATUS", "UPDATETIME", "ADMITTEDQUOTE", "LASTBID", "LASTOFFER", "LCLOSEPRICE", "LCURRENTPRICE", "MARKETPRICE2", "NUMBIDS", "NUMOFFERS", "CHANGE", "TIME", "HIGHBID", "LOWOFFER", "PRICEMINUSPREVWAPRICE", "OPENPERIODPRICE", "SEQNUM", "SYSTIME", "CLOSINGAUCTIONPRICE", "CLOSINGAUCTIONVOLUME", "ISSUECAPITALIZATION", "ISSUECAPITALIZATION_UPDATETIME", "ETFSETTLECURRENCY", "VALTODAY_RUR", "TRADINGSESSION"]
    #dt.index = c
    print(dt)
    # print(dt)
