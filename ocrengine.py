import io

import pytesseract
from bs4 import BeautifulSoup
from iso639 import Lang
from PIL import Image
from PySide6 import QtCore, QtGui

from ocr_result_block import OCRResultBlock


class OCREngine():
    def __init__(self, name: str):
        self.name = name
        self.languages = []

    def pixmap_to_pil(self, pixmap: QtGui.QPixmap) -> Image.Image:
        '''Convert into PIL image format'''
        bytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(bytes)
        buffer.open(QtCore.QIODevice.ReadWrite)
        # pixmap.save(buffer, 'PNG', 100)
        pixmap.save(buffer, 'BMP')
        pil_image = Image.open(io.BytesIO(buffer.data()))
        buffer.close()

        return pil_image

    def recognize_plain_text(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> str | None:
        return None

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English')) -> list[OCRResultBlock] | None:
        return None

# TODO: Implement https://github.com/sirfz/tesserocr


class OCREngineTesseract(OCREngine):
    def __init__(self) -> None:
        super().__init__('Tesseract')
        self.languages = pytesseract.get_languages()

    def parse_hocr(self, hocr: bytes, image_size: QtCore.QSize, px_per_mm: float) -> list[OCRResultBlock]:
        '''Parse box into result block'''
        soup = BeautifulSoup(hocr.decode(), 'html.parser')

        blocks = []

        for div in soup.find_all('div', class_='ocr_carea'):
            blocks.append(OCRResultBlock(image_size, px_per_mm, block=div))

        # Add safety margin sometimes needed for correct recognition
        margin = 5

        for block in blocks:
            block.bbox.adjust(-margin, -margin, margin, margin)

        return blocks

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English')) -> list[OCRResultBlock] | None:
        # TODO: get dpi from boxarea background
        # image.save('/tmp/1.png')
        # estimate: str = pytesseract.image_to_boxes(self.pixmap_to_pil(image))

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

        # words_rects = []
        # text = ''
        # height = 0
        # height_max = 0
        # estimate: dict = pytesseract.image_to_data(self.pixmap_to_pil(image), output_type=Output.DICT, lang=language.pt2t, config='--oem 2')

        hocr = pytesseract.image_to_pdf_or_hocr(self.pixmap_to_pil(image), extension='hocr', lang=language.pt2t)

        if isinstance(hocr, bytes):
            return self.parse_hocr(hocr, image.size(), px_per_mm)


class OCREngineManager():
    def __init__(self, engines=[]) -> None:
        self.engines = engines
        self.current_engine = engines[-1]

    def get_current_engine(self) -> OCREngine:
        return self.current_engine
