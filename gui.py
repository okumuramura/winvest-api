from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui
import requests
import matplotlib

matplotlib.use("Qt5Agg")

import math

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


import sys

class Requester(QtCore.QObject):
    finished = QtCore.Signal()
    result = QtCore.Signal(requests.Response)

    def __init__(self, parent: QtWidgets.QWidget, method: str, url: str, headers = None, body = None):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    def get(self):
        response = getattr(requests, self.method)(url = self.url, headers = self.headers, data = self.body)
        self.result.emit(response)
        self.finished.emit()
        return response

class StockPage(QtWidgets.QWidget):
    class MplCanvas(FigureCanvasQTAgg):
        def __init__(self, parent=None, width=5, height=3, dpi=100):
            fig = Figure(figsize = (width, height), dpi=dpi)
            self.axes = fig.add_subplot(111)
            super().__init__(fig)

    returned = QtCore.Signal()
    def __init__(self, id: int):
        super().__init__()
        self.stock_id = id
        self.prediction_plot = None
        self.loader = QtWidgets.QWidget()
        self.loader_label = QtWidgets.QLabel("Загрузка...")
        self.loader_label.setAlignment(QtCore.Qt.AlignCenter)

        self.loading_layout = QtWidgets.QVBoxLayout()
        self.loading_layout.addWidget(self.loader_label)
        self.loader.setLayout(self.loading_layout)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_label = QtWidgets.QLabel("Загрузка...")
        self.main_label.setAlignment(QtCore.Qt.AlignCenter)
        self.price_label = QtWidgets.QLabel("Текущая цена: ")
        self.change = QtWidgets.QWidget()
        self.change_layout = QtWidgets.QHBoxLayout()
        self.change_layout.setContentsMargins(0, 0, 0, 0)
        self.change_label = QtWidgets.QLabel("Разница с прошлым днём: ")
        self.change_procent = QtWidgets.QLabel("")
        self.change_layout.addWidget(self.change_label, 0, QtCore.Qt.AlignLeft)
        self.change_layout.addWidget(self.change_procent, 0, QtCore.Qt.AlignLeft)
        self.change.setLayout(self.change_layout)
        self.price_label.setAlignment(QtCore.Qt.AlignLeft)
        self.change_label.setAlignment(QtCore.Qt.AlignLeft)
        self.change_procent.setAlignment(QtCore.Qt.AlignLeft)
        self.main_layout.addWidget(self.main_label, 3, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

        #self.prediction_method = QtWidgets.QLabel("")
        self.prediction_method = QtWidgets.QComboBox()
        self.prediction_method.setMinimumWidth(300)
        self.prediction_method.setEnabled(False)
        self.prediction_method.currentIndexChanged.connect(self.method_changed)
        self.sc: Optional[FigureCanvasQTAgg] = None

        self.return_btn = QtWidgets.QPushButton("Назад")
        self.return_btn.setMaximumWidth(70)
        self.return_btn.clicked.connect(self.goback)

        self.data_layout = QtWidgets.QHBoxLayout()
        self.left_layout = QtWidgets.QVBoxLayout()
        self.right_layout = QtWidgets.QVBoxLayout()

        self.right_layout.addStretch(3)
        self.right_layout.addWidget(self.price_label, 1, QtCore.Qt.AlignLeft)
        self.right_layout.addWidget(self.change, 1, QtCore.Qt.AlignLeft)
        self.right_layout.addWidget(self.prediction_method, 1, QtCore.Qt.AlignLeft)
        self.right_layout.addStretch(9)

        self.data_layout.addLayout(self.left_layout, 3)
        self.data_layout.addLayout(self.right_layout, 1)

        #self.left_layout.addWidget(self.loader)

        self.main_layout.addLayout(self.data_layout, 10)

        self.main_layout.addWidget(self.return_btn, 3, QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)

        self.setLayout(self.main_layout)

        self.load_info()
        #self.draw_history(None)
        self.load_history()

    def load_info(self):
        #self.setCentralWidget(self.loader)
        self.th_info = QtCore.QThread()
        #self.setLayout(self.loading_layout)
        self.requester_info = Requester(self, "get", "http://127.0.0.1:8000/stocks/" + str(self.stock_id))
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
        #self.setLayout(self.loading_layout)
        self.requester_history = Requester(self, "get", "http://127.0.0.1:8000/history/stocks/" + str(self.stock_id))
        self.requester_history.moveToThread(self.th_history)
        self.th_history.started.connect(self.requester_history.get)
        self.requester_history.finished.connect(self.th_history.quit)
        self.th_history.finished.connect(self.th_history.deleteLater)
        self.requester_history.result.connect(self.draw_history)
        self.requester_history.finished.connect(self.load_predictions)
        self.th_history.start()


    def load_predictions(self):
        self.th_predictions = QtCore.QThread()
        #self.setLayout(self.loading_layout)
        self.requester_prediction = Requester(self, "get", "http://127.0.0.1:8000/predict/" + str(self.stock_id))
        self.requester_prediction.moveToThread(self.th_predictions)
        self.th_predictions.started.connect(self.requester_prediction.get)
        self.requester_prediction.finished.connect(self.th_predictions.quit)
        self.th_predictions.finished.connect(self.th_predictions.deleteLater)
        self.requester_prediction.result.connect(self.draw_predictions)
        self.th_predictions.start()

    def draw_info(self, data: requests.Response):
        if data.status_code == 200:
            info = data.json()
            self.name: str = info["fullname"]
            self.ticker: str = info["shortname"]
            self.price: Optional[float] = info["price"]
            self.change_volume: float = info["change"]
            self.main_label.setText(f"{self.ticker} {self.name}")
            price = str(self.price) + " руб." if self.price is not None else "-"
            self.price_label.setText("Текущая цена: " + price)
            self.change_procent.setText(f"{self.change_volume:+}%")
            if self.change_volume > 0:
                self.change_procent.setStyleSheet("color: rgb(0, 255, 0);")
            elif self.change_volume < 0:
                self.change_procent.setStyleSheet("color: rgb(255, 0, 0);")

    def draw_history(self, data: requests.Response):
        if data.status_code == 200:
            history = data.json()["history"]
            dates, value = zip(*history)
            self.history_len = len(value)
            self.sc = StockPage.MplCanvas()
            self.history_plot, = self.sc.axes.plot(list(range(len(value))), value)
            self.sc.axes.tick_params(
                axis='x',          # changes apply to the x-axis
                which='both',      # both major and minor ticks are affected
                bottom=False,      # ticks along the bottom edge are off
                top=False,         # ticks along the top edge are off
                labelbottom=False  # labels along the bottom edge are off
            )

            self.sc.draw()
            self.left_layout.removeWidget(self.loader)
            self.left_layout.addWidget(self.sc)

    def draw_predictions(self, data: requests.Response):
        if data.status_code == 200:
            methods = data.json()["methods"]
            try:
                #best_method = min(methods, key=lambda x: x["error"])
                self.methods = sorted(methods, key=lambda x: x["error"])
                best_method = self.methods[0]

                args = best_method["data"]
                tp = best_method["type"]
                predict_name = best_method["name"]

                #self.prediction_method.setText("Метод предсказания: " + predict_name)
                predictions_names = [x["name"] for x in self.methods]
                self.prediction_method.addItems(predictions_names)
                self.prediction_method.setEnabled(True)
            except ValueError:
                pass

    def method_changed(self, index: int):
        method = self.methods[index]

        args = method["data"]
        tp = method["type"]
        predict_name = method["name"]

        fs = {
            "lin": self.linear,
            "quad": self.quadratic,
            "log": self.logarithmic,
            "exp": self.exponential
        }
        if self.prediction_plot is not None:
            self.sc.axes.lines.remove(self.prediction_plot)
            self.sc.axes.relim(visible_only=True)
        
        if tp == "dots":
            ppv = args
            self.prediction_plot, = self.sc.axes.plot(list(range(self.history_len, self.history_len + len(args))), ppv, c="r")
            self.sc.draw()
        else:
            f = fs[tp]

            pv = [f(*args, x) for x in range(1, self.history_len + 1)]
            #ppv = [f(*args, x) for x in range(self.history_len, self.history_len + 61)]
            ppv = [f(*args, x) for x in range(1, self.history_len + 62)]
            self.prediction_plot, = self.sc.axes.plot(list(range(self.history_len + 61)), ppv, c="r")
            #self.sc.axes.plot(list(range(self.history_len)), pv)
            #self.prediction_plot, = self.sc.axes.plot(list(range(self.history_len, self.history_len + 61)), ppv, c="r")
            self.sc.draw()
            



    def goback(self, e):
        self.returned.emit()
        self.deleteLater()

    def linear(self, a, b, x):
        return a * x + b


    def quadratic(self, a, b, c, x):
        return a * x ** 2 + b * x + c


    def logarithmic(self, a, b, x):
        return a * math.log(x) + b


    def exponential(self, a, b, x):
        return a * math.exp(x) + b


class StocksList(QtWidgets.QWidget):
    class Stock(QtWidgets.QWidget):
        clicked = QtCore.Signal(int)
        def __init__(self, id: int, ticker: str, name: str, price: Optional[float], change: Optional[float]):
            super().__init__()
            self.id = id
            self.ticker = ticker
            self.name = name
            self.price = price
            self.change = change
            self.main_layout = QtWidgets.QHBoxLayout()

            self.tickerw = QtWidgets.QLabel(self.ticker)
            self.namew = QtWidgets.QLabel(self.name)
            price = self.price if self.price is not None else "-"
            change = f"{self.change:+}%" if self.change is not None else ""
            self.pricew = QtWidgets.QLabel(str(price))
            self.changew = QtWidgets.QLabel(str(change))

            self.main_layout.addWidget(self.tickerw, 1, QtCore.Qt.AlignLeft)
            self.main_layout.addWidget(self.namew, 5, QtCore.Qt.AlignLeft)
            self.main_layout.addWidget(self.pricew, 1, QtCore.Qt.AlignRight)
            self.main_layout.addWidget(self.changew, 1, QtCore.Qt.AlignRight)
            
            if self.change is not None:
                if self.change > 0:
                    self.changew.setStyleSheet("color: rgb(0, 255, 0);")
                elif self.change < 0:
                    self.changew.setStyleSheet("color: rgb(255, 0, 0);")

            self.setLayout(self.main_layout)

        def mousePressEvent(self, e: QtGui.QMouseEvent):
            self.clicked.emit(self.id)

        def enterEvent(self, event: QtGui.QEnterEvent) -> None:
            self.setStyleSheet("background: rgb(200, 200, 200);")

        def leaveEvent(self, event: QtCore.QEvent) -> None:
            self.setStyleSheet("background: rgba(255, 255, 255, 255);")
            
    clicked = QtCore.Signal(int)
    def __init__(self, parent):
        super().__init__()
        self.setMinimumSize(1280, 720)
        self.setStyleSheet("background: rgb(255, 255, 255);")
        self.parent = parent
        self.main_layout = QtWidgets.QVBoxLayout()
        self.loader = QtWidgets.QWidget(self)
        self.loader_label = QtWidgets.QLabel("Загрузка...")
        self.loader_label.setAlignment(QtCore.Qt.AlignCenter)

        self.loading_layout = QtWidgets.QVBoxLayout()
        self.loading_layout.addWidget(self.loader_label)
        self.loader.setLayout(self.loading_layout)

        self.stocklist = QtWidgets.QWidget()
        self.sll = QtWidgets.QVBoxLayout()
        self.scroller = QtWidgets.QScrollArea()
        self.scroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.sll.addWidget(self.scroller)

        self.stocks_layout = QtWidgets.QVBoxLayout()
        self.s = QtWidgets.QWidget()
        self.s.setLayout(self.stocks_layout)

        self.stocklist.setLayout(self.sll)
        

        self.stocks = []
        self.setLayout(self.main_layout)

        self.load()

    def load(self):
        self.main_layout.addWidget(self.loader)
        #self.setCentralWidget(self.loader)
        self.th = QtCore.QThread()
        #self.setLayout(self.loading_layout)
        self.requester = Requester(self, "get", "http://127.0.0.1:8000/stocks")
        self.requester.moveToThread(self.th)
        self.th.started.connect(self.requester.get)
        self.requester.finished.connect(self.th.quit)
        self.th.finished.connect(self.th.deleteLater)
        self.requester.result.connect(self.redraw)
        #self.th.finished.connect(self.redraw)
        self.th.start()

    def redraw(self, data: requests.Response):
        self.main_layout.removeWidget(self.loader)
        self.main_layout.addWidget(self.stocklist)

        if data.status_code == 200:
            stocks = data.json()["stocks"]
            for s in stocks:
                id = s["id"]
                ticker = s["shortname"]
                name = s["fullname"]
                price = s["price"]
                change = s["change"]
                owned = s["owned"]
                quantity = s["quantity"]
                st = StocksList.Stock(id, ticker, name, price, change)
                st.clicked.connect(self.stock_clicked)
                #print(id, ticker, name, price, change)
                self.stocks.append(st)
                self.stocks_layout.addWidget(st)

        self.scroller.setWidget(self.s)
        #self.setCentralWidget(self.stocklist)
        #self.setLayout(self.stocks_layout)

    def stock_clicked(self, id: int):
        self.clicked.emit(id)




class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: rgb(255, 255, 255);")
        self.setWindowTitle("Winvest v0.15")
        self.setGeometry(100, 100, 800, 600)
        # self.main_layout = QtWidgets.QVBoxLayout() 
        # self.header_layout = QtWidgets.QHBoxLayout()
        # self.header_layout.addSpacing(20)
        # self.stocker = StocksList(self)
        self.show_stocks_list()

        # self.main_layout.addLayout(self.header_layout)
        # self.main_layout.addWidget(self.stocker)

        # self.setLayout(self.main_layout)

    def stock_info(self, id: int):
        self.stock_page = StockPage(id)
        self.setCentralWidget(self.stock_page)
        self.stock_page.returned.connect(self.show_stocks_list)

    def show_stocks_list(self):
        self.stocker = StocksList(self)
        self.stocker.clicked.connect(self.stock_info)
        self.setCentralWidget(self.stocker)

app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
sys.exit(app.exec_())