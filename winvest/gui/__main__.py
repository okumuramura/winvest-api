import sys

from PyQt5 import QtWidgets

from winvest.gui.gui import MainWindow

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
