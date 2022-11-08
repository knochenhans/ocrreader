from PySide6 import QtWidgets, QtCore

from boxeditor import BoxEditor
from ocrengine import OCREngine
from propertyeditor import PropertyEditor

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1200, 800)
        self.setWindowTitle('PyOCR')
        self.show()

        self.engine = OCREngine('Tesseract')

        page_image_filename = '/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm'

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.property_editor = PropertyEditor(self)
        self.box_editor = BoxEditor(self, self.engine, self.property_editor, page_image_filename)
        self.box_editor.property_editor = self.property_editor
        self.property_editor.box_editor = self.box_editor


        self.splitter.addWidget(self.box_editor)
        self.splitter.addWidget(self.property_editor)
        self.setCentralWidget(self.splitter)
