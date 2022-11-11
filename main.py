import sys
from ocrreader import PyOCR
from mainwindow import MainWindow

if __name__ == '__main__':
    app = PyOCR(sys.argv)

    window = MainWindow()

    app.exec()
