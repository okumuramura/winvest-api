from typing import Any

import requests
from PyQt5 import QtCore, QtWidgets


class Requester(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    result = QtCore.pyqtSignal(requests.Response)

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        method: str,
        url: str,
        headers: Any = None,
        body: Any = None,
    ) -> None:
        super().__init__(parent=parent)
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    def get(self) -> requests.Response:
        response = getattr(requests, self.method)(
            url=self.url, headers=self.headers, data=self.body
        )
        self.result.emit(response)
        self.finished.emit()
        return response
