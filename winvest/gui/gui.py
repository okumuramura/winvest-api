import json
import math
import re
import sys
from typing import List, Optional

import matplotlib
import requests
from header import Header
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets
from requester import Requester

matplotlib.use('Qt5Agg')


class StockPage(QtWidgets.QWidget):
    class MplCanvas(FigureCanvasQTAgg):
        def __init__(self, parent=None, width=5, height=3, dpi=100):
            fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = fig.add_subplot(111)
            super().__init__(fig)

    returned = QtCore.Signal()

    def __init__(
        self,
        id: int,
        header: Optional[Header] = None,
        token: Optional[str] = None,
    ):
        super().__init__()
        self.stock_id = id
        self.prediction_plot = None
        self.header = header
        self.loader = QtWidgets.QWidget()
        self.loader_label = QtWidgets.QLabel('Загрузка...')
        self.loader_label.setAlignment(QtCore.Qt.AlignCenter)

        self.loading_layout = QtWidgets.QVBoxLayout()
        self.loading_layout.addWidget(self.loader_label)
        self.loader.setLayout(self.loading_layout)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_label = QtWidgets.QLabel('Загрузка...')
        self.main_label.setAlignment(QtCore.Qt.AlignCenter)
        self.price_label = QtWidgets.QLabel('Текущая цена: ')
        self.change = QtWidgets.QWidget()
        self.change_layout = QtWidgets.QHBoxLayout()
        self.change_layout.setContentsMargins(0, 0, 0, 0)
        self.change_label = QtWidgets.QLabel('Разница с прошлым днём: ')
        self.change_procent = QtWidgets.QLabel('')
        self.change_layout.addWidget(self.change_label, 0, QtCore.Qt.AlignLeft)
        self.change_layout.addWidget(
            self.change_procent, 0, QtCore.Qt.AlignLeft
        )
        self.change.setLayout(self.change_layout)
        self.price_label.setAlignment(QtCore.Qt.AlignLeft)
        self.change_label.setAlignment(QtCore.Qt.AlignLeft)
        self.change_procent.setAlignment(QtCore.Qt.AlignLeft)

        self.owned_row = QtWidgets.QHBoxLayout()
        self.owned_label = QtWidgets.QLabel('В наличии: ')
        self.owned_input = QtWidgets.QSpinBox()
        self.owned_input.setRange(1, 10000)
        self.owned_input.setEnabled(False)
        self.owned_row.addWidget(self.owned_label)
        self.owned_row.addWidget(self.owned_input)

        self.add_remove_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton('Добавить')
        self.remove_btn = QtWidgets.QPushButton('Удалить')
        self.add_btn.clicked.connect(self.add_stock)
        self.remove_btn.clicked.connect(self.remove_stock)
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.add_remove_row.addWidget(self.add_btn, 1)
        self.add_remove_row.addWidget(self.remove_btn, 1)

        if header is not None:
            self.main_layout.addWidget(self.header)
        self.token = token
        self.main_layout.addWidget(
            self.main_label, 3, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )

        # self.prediction_method = QtWidgets.QLabel('')
        self.prediction_method = QtWidgets.QComboBox()
        self.prediction_method.setMinimumWidth(300)
        self.prediction_method.setEnabled(False)
        self.prediction_method.currentIndexChanged.connect(self.method_changed)
        self.sc: Optional[FigureCanvasQTAgg] = None

        self.return_btn = QtWidgets.QPushButton('Назад')
        self.return_btn.setMaximumWidth(70)
        self.return_btn.clicked.connect(self.goback)

        self.data_layout = QtWidgets.QHBoxLayout()
        self.left_layout = QtWidgets.QVBoxLayout()
        self.right_layout = QtWidgets.QVBoxLayout()

        self.right_layout.addStretch(3)
        self.right_layout.addWidget(self.price_label, 1, QtCore.Qt.AlignLeft)
        self.right_layout.addWidget(self.change, 1, QtCore.Qt.AlignLeft)
        self.right_layout.addWidget(
            self.prediction_method, 1, QtCore.Qt.AlignLeft
        )
        if self.token is not None:
            self.right_layout.addLayout(self.owned_row)
            self.right_layout.addLayout(self.add_remove_row)
        self.right_layout.addStretch(9)

        self.data_layout.addLayout(self.left_layout, 3)
        self.data_layout.addLayout(self.right_layout, 1)

        self.main_layout.addLayout(self.data_layout, 10)

        self.main_layout.addWidget(
            self.return_btn, 3, QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter
        )

        self.setLayout(self.main_layout)

        self.load_info()
        self.load_history()

    def load_info(self):
        self.th_info = QtCore.QThread()
        auth_header = {}
        if self.token is not None:
            auth_header = {'authorization': self.token}
        self.requester_info = Requester(
            self,
            'get',
            'http://127.0.0.1:8000/stocks/' + str(self.stock_id),
            headers=auth_header,
        )
        self.requester_info.moveToThread(self.th_info)
        self.th_info.started.connect(self.requester_info.get)
        self.requester_info.finished.connect(self.th_info.quit)
        self.requester_info.finished.connect(self.requester_info.deleteLater)
        self.th_info.finished.connect(self.th_info.deleteLater)
        self.requester_info.result.connect(self.draw_info)
        self.th_info.start()

    def load_history(self):
        self.left_layout.removeWidget(self.loader)
        self.th_history = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester_history = Requester(
            self,
            'get',
            'http://127.0.0.1:8000/history/stocks/' + str(self.stock_id),
        )
        self.requester_history.moveToThread(self.th_history)
        self.th_history.started.connect(self.requester_history.get)
        self.requester_history.finished.connect(self.th_history.quit)
        self.th_history.finished.connect(self.th_history.deleteLater)
        self.requester_history.result.connect(self.draw_history)
        self.requester_history.finished.connect(self.load_predictions)
        self.th_history.start()

    def load_predictions(self):
        self.th_predictions = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester_prediction = Requester(
            self, 'get', 'http://127.0.0.1:8000/predict/' + str(self.stock_id)
        )
        self.requester_prediction.moveToThread(self.th_predictions)
        self.th_predictions.started.connect(self.requester_prediction.get)
        self.requester_prediction.finished.connect(self.th_predictions.quit)
        self.th_predictions.finished.connect(self.th_predictions.deleteLater)
        self.requester_prediction.result.connect(self.draw_predictions)
        self.th_predictions.start()

    def draw_info(self, data: requests.Response):
        if data.status_code == 200:
            info = data.json()
            self.name: str = info['fullname']
            self.ticker: str = info['shortname']
            self.price: Optional[float] = info['price']
            self.change_volume: float = info['change']
            self.owned: bool = info['owned']
            self.quantity: int = info['quantity']
            self.main_label.setText(f'{self.ticker} {self.name}')
            price = str(self.price) + ' руб.' if self.price is not None else '-'
            self.price_label.setText('Текущая цена: ' + price)
            self.change_procent.setText(f'{self.change_volume:+}%')
            if self.change_volume > 0:
                self.change_procent.setStyleSheet('color: rgb(0, 255, 0);')
            elif self.change_volume < 0:
                self.change_procent.setStyleSheet('color: rgb(255, 0, 0);')
            if not self.owned:
                self.owned_input.setValue(0)
                self.add_btn.setText('Добавить')
                self.add_btn.setEnabled(True)
                self.remove_btn.setEnabled(False)
            else:
                self.owned_input.setValue(self.quantity)
                self.add_btn.setText('Сохранить')
                self.add_btn.setEnabled(True)
                self.remove_btn.setEnabled(True)
            self.owned_input.setEnabled(True)

    def draw_history(self, data: requests.Response):
        if data.status_code == 200:
            history = data.json()['history']
            dates, value = zip(*history)
            self.history_len = len(value)
            self.sc = StockPage.MplCanvas()
            (self.history_plot,) = self.sc.axes.plot(
                list(range(len(value))), value
            )
            self.sc.axes.tick_params(
                axis='x',  # changes apply to the x-axis
                which='both',  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False,  # labels along the bottom edge are off
            )

            self.sc.draw()
            self.left_layout.removeWidget(self.loader)
            self.left_layout.addWidget(self.sc)

    def draw_predictions(self, data: requests.Response):
        if data.status_code == 200:
            methods = data.json()['methods']
            try:
                # best_method = min(methods, key=lambda x: x['error'])
                self.methods = sorted(methods, key=lambda x: x['error'])
                best_method = self.methods[0]

                args = best_method['data']
                tp = best_method['type']
                predict_name = best_method['name']

                # self.prediction_method.setText('Метод предсказания: ' + predict_name)
                predictions_names = [x['name'] for x in self.methods]
                self.prediction_method.addItems(predictions_names)
                self.prediction_method.setEnabled(True)
            except ValueError:
                pass

    def method_changed(self, index: int):
        method = self.methods[index]

        args = method['data']
        tp = method['type']
        predict_name = method['name']

        fs = {
            'lin': self.linear,
            'quad': self.quadratic,
            'log': self.logarithmic,
            'exp': self.exponential,
        }
        if self.prediction_plot is not None:
            self.sc.axes.lines.remove(self.prediction_plot)
            self.sc.axes.relim(visible_only=True)

        if tp == 'dots':
            ppv = args
            (self.prediction_plot,) = self.sc.axes.plot(
                list(range(self.history_len, self.history_len + len(args))),
                ppv,
                c='r',
            )
            self.sc.draw()
        else:
            f = fs[tp]

            pv = [f(*args, x) for x in range(1, self.history_len + 1)]
            # ppv = [f(*args, x) for x in range(self.history_len, self.history_len + 61)]
            ppv = [f(*args, x) for x in range(1, self.history_len + 62)]
            (self.prediction_plot,) = self.sc.axes.plot(
                list(range(self.history_len + 61)), ppv, c='r'
            )
            # self.sc.axes.plot(list(range(self.history_len)), pv)
            # self.prediction_plot, = self.sc.axes.plot(list(range(self.history_len, self.history_len + 61)), ppv, c='r')
            self.sc.draw()

    def add_stock(self):
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        if self.owned_input.value() <= 0:
            self.remove_stock()
            return

        self.th_add = QtCore.QThread()
        auth_header = {}
        if self.token is not None:
            body = json.dumps({'quantity': self.owned_input.value()})
            auth_header = {
                'authorization': self.token,
                'content-type': 'application/json',
            }
        self.requester_add = Requester(
            self,
            'post',
            'http://127.0.0.1:8000/stocks/add/' + str(self.stock_id),
            headers=auth_header,
            body=body,
        )
        self.requester_add.moveToThread(self.th_add)
        self.th_add.started.connect(self.requester_add.get)
        self.requester_add.finished.connect(self.th_add.quit)
        self.requester_add.finished.connect(self.requester_add.deleteLater)
        self.th_add.finished.connect(self.th_add.deleteLater)
        self.requester_add.result.connect(self.stock_updated)
        self.th_add.start()

    def remove_stock(self):
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

        self.th_rem = QtCore.QThread()
        auth_header = {}
        if self.token is not None:
            auth_header = {'authorization': self.token}
        self.requester_rem = Requester(
            self,
            'post',
            'http://127.0.0.1:8000/stocks/remove/' + str(self.stock_id),
            headers=auth_header,
        )
        self.requester_rem.moveToThread(self.th_rem)
        self.th_rem.started.connect(self.requester_rem.get)
        self.requester_rem.finished.connect(self.th_rem.quit)
        self.requester_rem.finished.connect(self.requester_rem.deleteLater)
        self.th_rem.finished.connect(self.th_rem.deleteLater)
        self.requester_rem.result.connect(self.stock_removed)
        self.th_rem.start()

    def stock_updated(self, response: requests.Response):
        self.add_btn.setEnabled(True)
        self.add_btn.setText('Сохранить')
        self.remove_btn.setEnabled(True)

    def stock_removed(self, response: requests.Response):
        self.owned_input.setValue(0)
        self.add_btn.setText('Добавить')
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(False)

    def goback(self, e):
        self.returned.emit()
        self.deleteLater()

    def linear(self, a, b, x):
        return a * x + b

    def quadratic(self, a, b, c, x):
        return a * x**2 + b * x + c

    def logarithmic(self, a, b, x):
        return a * math.log(x) + b

    def exponential(self, a, b, x):
        return a * math.exp(x) + b


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
    ):
        self.id = id
        self.ticker = ticker
        self.name = name
        self.price = price
        self.change = change
        self.owned = owned
        self.quantity = quantity


class StocksList(QtWidgets.QWidget):
    stock_selected = QtCore.Signal(int)

    class Delegate(QtWidgets.QStyledItemDelegate):
        def __init__(self):
            super().__init__()
            self.need_calculate = True

        def set_need_calculate(self, value: bool):
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

                # painter.drawText(option.rect, 1, f'{stock.ticker} {stock.name} {stock.price:.2f}')
            return super().paint(painter, option, index)

    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ):
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

    def load_stocks(self):
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
        # self.th.finished.connect(self.redraw)
        self.th.start()

    def redraw(self, response: requests.Response):
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
                owned = s['owned']
                quantity = s['quantity']
                st = Stock(id, ticker, name, price, change)
                # st.clicked.connect(self.stock_clicked)
                self.stocks.append(st)
                self.stock_item = QtWidgets.QListWidgetItem()
                self.stock_item.setData(0, st)
                self.stock_list.addItem(self.stock_item)

    def apply_filter(self, query: str):
        pattern = re.compile(query, re.IGNORECASE)
        self.stock_list.clear()

        for stock in self.stocks:
            if pattern.search(stock.ticker + ' ' + stock.name) is not None:
                self.stock_item = QtWidgets.QListWidgetItem()
                self.stock_item.setData(0, stock)
                self.stock_list.addItem(self.stock_item)

    def item_clicked(self, item: QtWidgets.QListWidgetItem):
        stock: Stock = item.data(0)
        self.stock_selected.emit(stock.id)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.delegate.need_calculate = True


class NewStocksList(StocksList):
    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ):
        super().__init__(token=token, header=header)


class Portfolio(StocksList):
    def __init__(
        self, token: Optional[str] = None, header: Optional[Header] = None
    ):
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

    def load_stocks(self):
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

    def complete_header(self, response: requests.Response):
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
    def __init__(self):
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

    def stock_info(self, id: int):
        aw = self.active_window
        self.active_window == 2
        self.stock_page = StockPage(id, self.header, token=self.token)
        self.setCentralWidget(self.stock_page)
        if aw == 0:
            self.stock_page.returned.connect(self.show_stocks_list)
        elif aw == 1:
            self.stock_page.returned.connect(self.show_portfolio)

    def show_stocks_list(self):
        self.active_window = 0
        self.stocker = NewStocksList(header=self.header)
        self.stocker.stock_selected.connect(self.stock_info)
        self.setCentralWidget(self.stocker)

    def show_portfolio(self):
        self.active_window = 1
        self.portfolio = Portfolio(token=self.token, header=self.header)
        self.portfolio.stock_selected.connect(self.stock_info)
        self.setCentralWidget(self.portfolio)

    def logged_in(self, username: str, token: str):
        self.username = username
        self.token = token

    def logged_out(self):
        self.username = None
        self.token = None
        if self.active_window == 1:
            self.show_stocks_list()

    def search(self, pattern: str):
        if self.active_window == 0:
            self.stocker.apply_filter(pattern)
        elif self.active_window == 1:
            self.portfolio.apply_filter(pattern)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
