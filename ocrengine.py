import io
import re

import pytesseract
from pytesseract import Output
from iso639 import Lang
from PIL import Image
from PySide6 import QtCore, QtGui


class OCREngine():
    def __init__(self, name: str):
        self.name = name

    def pixmap_to_pil(self, pixmap: QtGui.QPixmap) -> Image.Image:
        '''Convert into PIL image format'''
        bytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(bytes)
        buffer.open(QtCore.QIODevice.ReadWrite)
        pixmap.save(buffer, 'PNG', 100)
        pil_image = Image.open(io.BytesIO(buffer.data()))
        buffer.close()

        return pil_image

    def read(self, image: QtGui.QPixmap, language: str) -> str:
        return pytesseract.image_to_string(self.pixmap_to_pil(image), lang=language)

    def estimate(self, image: QtGui.QPixmap) -> QtCore.QRect | None:
        # image.save('/tmp/1.png')
        # estimate: str = pytesseract.image_to_boxes(self.pixmap_to_pil(image))

        words_rects = []

        # for line in estimate.splitlines():
        #     # char left bottom right top page -> top left / bottom right
        #     m = re.match(r'(.) (\d+) (\d+) (\d+) (\d+) (\d+)', line)

        #     if m:
        #         character = m.group(1)
        #         rects.append(QtCore.QRect(int(m.group(5)), int(m.group(2)), int(m.group(3)), int(m.group(4))))
        #         page = m.group(6)

        # if rects:
        #     # Return top left position of first character and bottom right position of last character
        #     return QtCore.QRect(rects[0].x(), rects[0].y(), rects[-1].right(), rects[-1].bottom())
        estimate: dict = pytesseract.image_to_data(self.pixmap_to_pil(image), output_type=Output.DICT)

        boxes = len(estimate['level'])

        for i in range(boxes):
            if estimate['level'][i] == 5 and estimate['conf'][i] > 50:
                (x, y, w, h) = (estimate['left'][i], estimate['top'][i], estimate['width'][i], estimate['height'][i])
                words_rects.append(QtCore.QRect(x, y, w, h))

        if words_rects:
            margin = 10

            # Get most outer coordinates for all recognized words
            words_rects.sort(key=lambda x: x.top(), reverse=True)

            top = words_rects[-1].top() - margin

            words_rects.sort(key=lambda x: x.left(), reverse=True)

            left = words_rects[-1].left() - margin
            
            words_rects.sort(key=lambda x: x.bottom())

            bottom = words_rects[-1].bottom() + margin
            
            words_rects.sort(key=lambda x: x.right())

            right = words_rects[-1].right() + margin

            return QtCore.QRect(QtCore.QPoint(left, top), QtCore.QPoint(right, bottom))
