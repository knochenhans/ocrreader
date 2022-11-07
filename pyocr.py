from PySide6 import QtCore, QtGui, QtWidgets


class PyOCR(QtWidgets.QApplication):
    def __init__(self, argv) -> None:
        super().__init__(argv)
