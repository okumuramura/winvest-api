import requests
from PyQt5 import QtCore, QtWidgets


class Requester(QtCore.QObject):
    finished = QtCore.Signal()
    result = QtCore.Signal(requests.Response)

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        method: str,
        url: str,
        headers=None,
        body=None,
    ):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    def get(self):
        response = getattr(requests, self.method)(
            url=self.url, headers=self.headers, data=self.body
        )
        self.result.emit(response)
        self.finished.emit()
        return response
