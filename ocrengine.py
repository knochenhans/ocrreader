import io
import pytesseract
from PySide6 import QtGui, QtCore
from PIL import Image
from iso639 import Lang

class OCREngine():
    def __init__(self, name: str):
        self.name = name

    def read(self, image: QtGui.QPixmap, language: str) -> str:
        # Convert into PIL image format
        bytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(bytes)
        buffer.open(QtCore.QIODevice.ReadWrite)
        image.save(buffer, 'PNG', 100)
        pil_image = Image.open(io.BytesIO(buffer.data()))
        buffer.close()

        return pytesseract.image_to_string(pil_image, lang=language)