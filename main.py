import sys

from PySide6 import QtCore

from mainwindow import MainWindow
from ocrreader import PyOCR

if __name__ == '__main__':
    app = PyOCR(sys.argv)

    translator = QtCore.QTranslator()

    if translator.load('mainwindow_de'):
        QtCore.QCoreApplication.installTranslator(translator)

    window = MainWindow()

    app.exec()
