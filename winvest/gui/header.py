import json

import requests
from PyQt5 import QtCore, QtGui, QtWidgets
from requester import Requester


class Header(QtWidgets.QWidget):
    class RegisterWindow(QtWidgets.QDialog):
        class Types:
            REGISTER = 0
            LOGIN = 1

        result = QtCore.Signal(str, str)

        def __init__(self, title: str, _type: int):
            super().__init__()
            self.setWindowTitle(title)
            self.type = _type
            self.setModal(True)
            self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
            self.dialog_layout = QtWidgets.QFormLayout()
            self.login_input = QtWidgets.QLineEdit()
            self.password_input = QtWidgets.QLineEdit()
            self.password_input.setEchoMode(
                QtWidgets.QLineEdit.EchoMode.Password
            )
            self.submit_btn = QtWidgets.QPushButton("Применить")
            self.submit_btn.clicked.connect(self.submit)

            self.dialog_layout.addRow("Имя пользователя", self.login_input)
            self.dialog_layout.addRow("Пароль", self.password_input)
            self.dialog_layout.addWidget(self.submit_btn)

            self.setLayout(self.dialog_layout)

        def submit(self):
            self.submit_btn.setEnabled(False)
            if self.type == Header.RegisterWindow.Types.REGISTER:
                self.__submit_register()
            else:
                self.__submit_login()

        def __submit_register(self):
            self.register_body = {
                "login": self.login_input.text(),
                "password": self.password_input.text(),
            }
            print(self.register_body)
            self.th_register = QtCore.QThread()
            self.requester_register = Requester(
                self,
                "post",
                "http://127.0.0.1:8000/register",
                headers={"Content-Type": "application/json"},
                body=json.dumps(self.register_body),
            )
            self.requester_register.moveToThread(self.th_register)
            self.th_register.started.connect(self.requester_register.get)
            self.requester_register.finished.connect(self.th_register.quit)
            self.th_register.finished.connect(self.th_register.deleteLater)
            self.requester_register.result.connect(self.register_complete)
            self.th_register.start()

        def register_complete(self, response: requests.Response):
            if response.status_code == 200:
                self.__submit_login()
            else:
                try:
                    detail = response.json()["detail"]
                except:
                    detail = "Unknown error"
                self.error = QtWidgets.QMessageBox()
                self.error.setWindowTitle("Ошибка регистрации")
                self.error.setText("Error: " + detail)
                self.error.show()
                self.submit_btn.setEnabled(True)

        def __submit_login(self):
            self.query = self.login_input.text()
            self.register_body = {
                "login": self.login_input.text(),
                "password": self.password_input.text(),
            }
            self.th_login = QtCore.QThread()
            self.requester_login = Requester(
                self,
                "post",
                "http://127.0.0.1:8000/login",
                headers={"Content-Type": "application/json"},
                body=json.dumps(self.register_body),
            )
            self.requester_login.moveToThread(self.th_login)
            self.th_login.started.connect(self.requester_login.get)
            self.requester_login.finished.connect(self.th_login.quit)
            self.th_login.finished.connect(self.th_login.deleteLater)
            self.requester_login.result.connect(self.login_complete)
            self.th_login.start()

        def login_complete(self, response: requests.Response):
            if response.status_code == 200:
                token: str = response.json()["token"]
                self.result.emit(self.query, token)
                self.close()
            else:
                try:
                    detail = response.json()["detail"]
                except:
                    detail = "Unknown error"
                self.error = QtWidgets.QMessageBox()
                self.error.setWindowTitle("Ошибка входа")
                self.error.setText("Error: " + detail)
                self.error.show()
                self.submit_btn.setEnabled(True)

    loggedin = QtCore.Signal(str, str)
    loggedout = QtCore.Signal()
    searched = QtCore.Signal(str)
    portfolio = QtCore.Signal()
    title = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setMaximumHeight(100)
        self.logged_in = False
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Поиск")
        # self.search_input.returnPressed.connect(self.search_activate)
        self.search_input.textChanged.connect(self.search_activate)

        self.icon = QtWidgets.QLabel()
        self.icon_font = QtGui.QFont()
        self.icon_font.setBold(True)
        self.icon_font.setPointSize(21)
        self.icon.setFont(self.icon_font)
        self.icon.setText("Winvest")
        self.icon.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        self.icon.mouseReleaseEvent = lambda x: self.title.emit()

        self.right_button = QtWidgets.QPushButton("Регистрация")
        self.left_button = QtWidgets.QPushButton("Вход")

        # self.portfolio_button = QtWidgets.QPushButton("Портфель")
        # self.logout_button = QtWidgets.QPushButton("Выйти")
        self.button_layout = QtWidgets.QHBoxLayout()
        self.setStyleSheet(
            """
            QWidget {
                background: white;
            }
            QPushButton {
                background-color: white;
                border-style: none;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
            """
        )

        self.button_layout.addWidget(self.left_button)
        self.button_layout.addWidget(self.right_button)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addWidget(self.icon, 10, QtCore.Qt.AlignLeft)
        self.main_layout.addWidget(self.search_input, 50, QtCore.Qt.AlignCenter)
        self.main_layout.addStretch(10)
        self.main_layout.addLayout(self.button_layout)

        self.change_buttons_layout()

        self.setLayout(self.main_layout)

    def open_register_window(self):
        self.register_window = Header.RegisterWindow(
            "Регистрация", Header.RegisterWindow.Types.REGISTER
        )
        self.register_window.result.connect(self.login_done)
        self.register_window.show()

    def open_login_window(self):
        self.login_window = Header.RegisterWindow(
            "Вход", Header.RegisterWindow.Types.LOGIN
        )
        self.login_window.result.connect(self.login_done)
        self.login_window.show()

    def login_done(self, username: str, token: str):
        self.logged_in = True
        self.username = username
        self.loggedin.emit(username, token)
        self.change_buttons_layout()

    def logout(self):
        self.logged_in = False
        self.loggedout.emit()
        self.change_buttons_layout()

    def open_portfolio(self):
        self.portfolio.emit()

    def change_buttons_layout(self):
        if self.logged_in:
            self.left_button.setText("Портфель[%s]" % self.username)
            self.left_button.clicked.disconnect(self.open_login_window)
            self.left_button.clicked.connect(self.open_portfolio)
            self.right_button.setText("Выйти")
            self.right_button.clicked.disconnect(self.open_register_window)
            self.right_button.clicked.connect(self.logout)
        else:
            self.left_button.setText("Войти")
            try:
                self.left_button.clicked.disconnect(self.open_portfolio)
            except:
                pass
            self.left_button.clicked.connect(self.open_login_window)
            self.right_button.setText("Регистрация")
            try:
                self.right_button.clicked.disconnect(self.logout)
            except:
                pass
            self.right_button.clicked.connect(self.open_register_window)

    def search_activate(self):
        self.searched.emit(self.search_input.text())