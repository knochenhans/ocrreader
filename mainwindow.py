from PySide6 import QtWidgets

from boxeditor import BoxEditor
from ocrengine import OCREngine


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1200, 800)
        self.setWindowTitle('PyOCR')
        self.show()

        self.engine = OCREngine('Tesseract')

        self.setCentralWidget(BoxEditor(self, self.engine))
