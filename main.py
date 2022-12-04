import sys

from PySide6 import QtCore

from main_window import MainWindow
from ocrreader import PyOCR

if __name__ == '__main__':
    app = PyOCR(sys.argv)

    translator = QtCore.QTranslator()

    if translator.load(QtCore.QLocale().system(), 'ocrreader', '_', '.'):
        QtCore.QCoreApplication.installTranslator(translator)

    window = MainWindow()

    app.exec()
