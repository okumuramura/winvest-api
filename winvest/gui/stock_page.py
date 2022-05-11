import json
import math
from typing import Optional, Any

import requests
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtWidgets

from winvest.gui import logger, URLs
from winvest.gui.header import Header
from winvest.gui.requester import Requester


class StockPage(QtWidgets.QWidget):
    class MplCanvas(FigureCanvasQTAgg):
        def __init__(
            self, width: int = 5, height: int = 3, dpi: int = 100
        ) -> None:
            fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = fig.add_subplot(111)
            super().__init__(fig)

    returned = QtCore.pyqtSignal()

    def __init__(
        self,
        id: int,
        header: Optional[Header] = None,
        token: Optional[str] = None,
    ) -> None:
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

    def load_info(self) -> None:
        self.th_info = QtCore.QThread()
        auth_header = {}
        if self.token is not None:
            auth_header = {'authorization': self.token}
        self.requester_info = Requester(
            self,
            'get',
            URLs.STOCK_PAGE % self.stock_id,
            headers=auth_header,
        )
        logger.info('loading info...')
        self.requester_info.moveToThread(self.th_info)
        self.th_info.started.connect(self.requester_info.get)
        self.requester_info.finished.connect(self.th_info.quit)
        self.requester_info.finished.connect(self.requester_info.deleteLater)
        self.th_info.finished.connect(self.th_info.deleteLater)
        self.requester_info.result.connect(self.draw_info)
        self.th_info.start()

    def load_history(self) -> None:
        self.left_layout.removeWidget(self.loader)
        self.th_history = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester_history = Requester(
            self,
            'get',
            URLs.HISTORY_LOAD % self.stock_id,
        )
        logger.info('loading history for stock with id %d', self.stock_id)
        self.requester_history.moveToThread(self.th_history)
        self.th_history.started.connect(self.requester_history.get)
        self.requester_history.finished.connect(self.th_history.quit)
        self.th_history.finished.connect(self.th_history.deleteLater)
        self.requester_history.result.connect(self.draw_history)
        self.requester_history.finished.connect(self.load_predictions)
        self.th_history.start()

    def load_predictions(self) -> None:
        self.th_predictions = QtCore.QThread()
        # self.setLayout(self.loading_layout)
        self.requester_prediction = Requester(
            self, 'get', URLs.PREDICT % self.stock_id
        )
        logger.info('loading predictions for stock with id %d', self.stock_id)
        self.requester_prediction.moveToThread(self.th_predictions)
        self.th_predictions.started.connect(self.requester_prediction.get)
        self.requester_prediction.finished.connect(self.th_predictions.quit)
        self.th_predictions.finished.connect(self.th_predictions.deleteLater)
        self.requester_prediction.result.connect(self.draw_predictions)
        self.th_predictions.start()

    def draw_info(self, data: requests.Response) -> None:
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

    def draw_history(self, data: requests.Response) -> None:
        if data.status_code == 200:
            history = data.json()['history']
            _, value = zip(*history)
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

    def draw_predictions(self, data: requests.Response) -> None:
        if data.status_code == 200:
            methods = data.json()['methods']
            try:
                self.methods = sorted(methods, key=lambda x: x['error'])
                best_method = self.methods[0]

                _ = best_method['data']
                _ = best_method['type']
                _ = best_method['name']

                # self.prediction_method.setText(
                # 'Метод предсказания: ' + predict_name)
                predictions_names = [x['name'] for x in self.methods]
                self.prediction_method.addItems(predictions_names)
                self.prediction_method.setEnabled(True)
            except ValueError:
                pass

    def method_changed(self, index: int) -> None:
        method = self.methods[index]

        args = method['data']
        tp = method['type']
        _ = method['name']

        fs = {
            'lin': self.linear,
            'quad': self.quadratic,
            'log': self.logarithmic,
            'exp': self.exponential,
        }
        if self.sc is None:
            return

        if self.prediction_plot is not None:
            self.sc.axes.lines.remove(self.prediction_plot)
            self.sc.axes.relim(visible_only=True)

        if tp == 'dots':
            plot_values = args
            (self.prediction_plot,) = self.sc.axes.plot(
                list(range(self.history_len, self.history_len + len(args))),
                plot_values,
                c='r',
            )
            self.sc.draw()
        else:
            f: Any = fs[tp]

            _ = [f(*args, x) for x in range(1, self.history_len + 1)]
            plot_values = [f(*args, x) for x in range(1, self.history_len + 62)]
            (self.prediction_plot,) = self.sc.axes.plot(
                list(range(self.history_len + 61)), plot_values, c='r'
            )
            self.sc.draw()

    def add_stock(self) -> None:
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
            URLs.ADD_STOCK % self.stock_id,
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

    def remove_stock(self) -> None:
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

        self.th_rem = QtCore.QThread()
        auth_header = {}
        if self.token is not None:
            auth_header = {'authorization': self.token}
        self.requester_rem = Requester(
            self,
            'delete',
            URLs.DELETE_STOCK % self.stock_id,
            headers=auth_header,
        )
        self.requester_rem.moveToThread(self.th_rem)
        self.th_rem.started.connect(self.requester_rem.get)
        self.requester_rem.finished.connect(self.th_rem.quit)
        self.requester_rem.finished.connect(self.requester_rem.deleteLater)
        self.th_rem.finished.connect(self.th_rem.deleteLater)
        self.requester_rem.result.connect(self.stock_removed)
        self.th_rem.start()

    def stock_updated(self, response: requests.Response) -> None:
        logger.info('stock info updated')
        self.add_btn.setEnabled(True)
        self.add_btn.setText('Сохранить')
        self.remove_btn.setEnabled(True)

    def stock_removed(self, response: requests.Response) -> None:
        logger.info('stock removed from portfolio')
        self.owned_input.setValue(0)
        self.add_btn.setText('Добавить')
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(False)

    def goback(self, _: Any) -> None:
        self.returned.emit()
        self.deleteLater()

    def linear(self, a: float, b: float, x: float) -> float:
        return a * x + b

    def quadratic(self, a: float, b: float, c: float, x: float) -> float:
        return a * x**2 + b * x + c

    def logarithmic(self, a: float, b: float, x: float) -> float:
        return a * math.log(x) + b

    def exponential(self, a: float, b: float, x: float) -> float:
        return a * math.exp(x) + b
