import re
import sys
from typing import List, Optional

import matplotlib
import requests
from PyQt5 import QtCore, QtGui, QtWidgets

from winvest.gui.header import Header
from winvest.gui.requester import Requester
from winvest.gui.stock_page import StockPage

matplotlib.use('Qt5Agg')


class Stock:
    def __init__(
        self,
        id: int,
        ticker: str,
        name: str,
        price: float,
        change: float,
        owned: bool = False,
        quantity: int = 0,
    ) -> None:
        self.id = id
        self.ticker = ticker
        self.name = name
        self.price = price
        self.change = change
        self.owned = owned
        self.quantity = quantity


class StocksList(QtWidgets.QWidget):
    stock_selected = QtCore.pyqtSignal(int)

    class Delegate(QtWidgets.QStyledItemDelegate):
        def __init__(self) -> None:
            super().__init__()
            self.need_calculate = True

        def set_need_calculate(self, value: bool) -> None:
            self.need_calculate = value

        def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex,
        ) -> None:
            if type(index.data()) == Stock:
                stock: Stock = index.data()
                rect: QtCore.QRect = option.rect
                t = rect.width() // 10
                if self.need_calculate:
                    self.ticker_right = t
                    self.name_right = self.ticker_right + int(
                        rect.width() // 1.4
                    )
                    self.price_right = self.name_right + t
                ticker_rect = QtCore.QRect(
                    rect.topLeft(), QtCore.QSize(t, rect.height())
                )
                name_rect = QtCore.QRect(
                    QtCore.QPoint(ticker_rect.width(), rect.top()),
                    QtCore.QSize(int(rect.width() // 1.4), rect.height()),
                )
                price_rect = QtCore.QRect(
                    QtCore.QPoint(name_rect.right(), rect.top()),
                    QtCore.QSize(t, rect.height()),
                )
                change_rect = QtCore.QRect(
                    QtCore.QPoint(price_rect.right(), rect.top()),
                    QtCore.QSize(t, rect.height()),
                )

                painter.drawText(ticker_rect, 0, stock.ticker)
                painter.drawText(name_rect, 0, stock.name)
                painter.drawText(
                    price_rect,
                    0,
                    (
                        str(stock.price) + ' руб.'
                        if stock.price is not None
                        else '-'
                    ),
                )

                pen = QtGui.QPen()
                if stock.change > 0:
                    pen.setColor(QtCore.Qt.green)
                elif stock.change < 0:
                    pen.setColor(QtCore.Qt.red)

                painter.setPen(pen)
                painter.drawText(change_rect, 0, f'{stock.change:+.1f}%')
                pen.setColor(QtCore.Qt.black)
                painter.setPen(pen)

            super().paint(painter, option, index)

    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ) -> None:
        super().__init__()
        self.setMinimumSize(1280, 720)
        self.stocks: List[Stock] = []
        self.loader_label = QtWidgets.QLabel('Загрузка...')
        self.loader_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loader_label.setMinimumSize(1280, 720)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.header = header
        if self.header is not None:
            self.main_layout.addWidget(self.header)
        self.stock_list = QtWidgets.QListWidget()
        self.stock_list.itemDoubleClicked.connect(self.item_clicked)
        self.delegate = NewStocksList.Delegate()
        self.stock_list.setItemDelegate(self.delegate)
        self.main_layout.addWidget(self.loader_label)
        self.token = token

        self.load_stocks()

        self.setLayout(self.main_layout)

    def load_stocks(self) -> None:
        # self.main_layout.addWidget(self.loader)
        # self.setCentralWidget(self.loader)
        self.th = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester = Requester(self, 'get', 'http://127.0.0.1:8000/stocks')
        self.requester.moveToThread(self.th)
        self.th.started.connect(self.requester.get)
        self.requester.finished.connect(self.th.quit)
        self.th.finished.connect(self.th.deleteLater)
        self.requester.result.connect(self.redraw)
        self.th.start()

    def redraw(self, response: requests.Response) -> None:
        self.main_layout.removeWidget(self.loader_label)
        self.main_layout.addWidget(self.stock_list)

        if response.status_code == 200:
            stocks = response.json()['stocks']
            for s in stocks:
                id = s['id']
                ticker = s['shortname']
                name = s['fullname']
                price = s['price']
                change = s['change']
                _ = s['owned']
                _ = s['quantity']
                st = Stock(id, ticker, name, price, change)
                # st.clicked.connect(self.stock_clicked)
                self.stocks.append(st)
                self.stock_item = QtWidgets.QListWidgetItem()
                self.stock_item.setData(0, st)
                self.stock_list.addItem(self.stock_item)

    def apply_filter(self, query: str) -> None:
        pattern = re.compile(query, re.IGNORECASE)
        self.stock_list.clear()

        for stock in self.stocks:
            if pattern.search(stock.ticker + ' ' + stock.name) is not None:
                self.stock_item = QtWidgets.QListWidgetItem()
                self.stock_item.setData(0, stock)
                self.stock_list.addItem(self.stock_item)

    def item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        stock: Stock = item.data(0)
        self.stock_selected.emit(stock.id)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.delegate.need_calculate = True


class NewStocksList(StocksList):
    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ) -> None:
        super().__init__(token=token, header=header)


class Portfolio(StocksList):
    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ) -> None:
        super().__init__(token=token, header=header)
        self.portfolio_header = QtWidgets.QHBoxLayout()
        self.portfolio_owner = QtWidgets.QLabel('Портфель')
        self.portfolio_cost = QtWidgets.QLabel('')
        self.portfolio_profit = QtWidgets.QLabel('Прибыль: 0 руб.')
        self.portfolio_profit.setToolTip(
            'Общая прибыль считается с момента добавления акций в портфель'
        )
        self.portfolio_owner.setAlignment(QtCore.Qt.AlignLeft)
        self.portfolio_cost.setAlignment(QtCore.Qt.AlignRight)
        self.portfolio_profit.setAlignment(QtCore.Qt.AlignRight)
        self.portfolio_header.addWidget(self.portfolio_owner, 3)
        self.portfolio_header.addWidget(self.portfolio_cost, 1)
        self.portfolio_header.addWidget(self.portfolio_profit, 1)
        self.main_layout.addLayout(self.portfolio_header)

    def load_stocks(self) -> None:
        self.th = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester = Requester(
            self,
            'get',
            'http://127.0.0.1:8000/portfolio',
            headers={'authorization': self.token},
        )
        self.requester.moveToThread(self.th)
        self.th.started.connect(self.requester.get)
        self.requester.finished.connect(self.th.quit)
        self.th.finished.connect(self.th.deleteLater)
        self.requester.result.connect(self.redraw)
        self.requester.result.connect(self.complete_header)
        # self.th.finished.connect(self.redraw)
        self.th.start()

    def complete_header(self, response: requests.Response) -> None:
        if response.status_code == 200:
            json_response = response.json()
            total_cost = float(json_response['total_value'])
            total_profit = float(json_response['total_profit'])
            owner_name = json_response['username']
            self.portfolio_cost.setText(
                f'Общая стоимость: {total_cost:.2f} руб.'
            )
            self.portfolio_owner.setText('Портфель ' + owner_name)
            self.portfolio_profit.setText(f'Прибыль: {total_profit:.2f} руб.')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet('background: rgb(255, 255, 255);')
        self.setWindowTitle('Winvest v0.17')
        self.setGeometry(100, 100, 800, 600)
        self.token = None
        self.header = Header()
        self.header.loggedin.connect(self.logged_in)
        self.header.loggedout.connect(self.logged_out)
        self.header.searched.connect(self.search)
        self.header.portfolio.connect(self.show_portfolio)
        self.header.title.connect(self.show_stocks_list)
        self.show_stocks_list()

    def stock_info(self, id: int) -> None:
        aw = self.active_window
        self.active_window == 2
        self.stock_page = StockPage(id, self.header, token=self.token)
        self.setCentralWidget(self.stock_page)
        if aw == 0:
            self.stock_page.returned.connect(self.show_stocks_list)
        elif aw == 1:
            self.stock_page.returned.connect(self.show_portfolio)

    def show_stocks_list(self) -> None:
        self.active_window = 0
        self.stocker = NewStocksList(header=self.header)
        self.stocker.stock_selected.connect(self.stock_info)
        self.setCentralWidget(self.stocker)

    def show_portfolio(self) -> None:
        self.active_window = 1
        self.portfolio = Portfolio(token=self.token, header=self.header)
        self.portfolio.stock_selected.connect(self.stock_info)
        self.setCentralWidget(self.portfolio)

    def logged_in(self, username: str, token: str) -> None:
        self.username = username
        self.token = token

    def logged_out(self) -> None:
        self.username = None
        self.token = None
        if self.active_window == 1:
            self.show_stocks_list()

    def search(self, pattern: str) -> None:
        if self.active_window == 0:
            self.stocker.apply_filter(pattern)
        elif self.active_window == 1:
            self.portfolio.apply_filter(pattern)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
