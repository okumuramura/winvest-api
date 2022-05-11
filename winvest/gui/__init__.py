import logging

logger = logging.Logger(__name__)

API_URL = 'http://127.0.0.1:8000'


class URLs:
    API_TEMP = API_URL + '%s'

    STOCKS_LIST = API_TEMP % '/stocks/'
    STOCK_PAGE = API_TEMP % '/stocks/%d'
    PORTFOLIO = API_TEMP % '/portfolio'
    HISTORY_LOAD = API_TEMP % '/history/stocks/%d'
    PREDICT = API_TEMP % '/predict/%d'
    ADD_STOCK = API_TEMP % '/portfolio/add/%d'
    DELETE_STOCK = API_TEMP % '/portfolio/%d'
    LOGIN = API_TEMP % '/login'
    REGISTER = API_TEMP % '/register'
