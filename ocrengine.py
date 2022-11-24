import io

import cv2
import numpy
import pytesseract
from bs4 import BeautifulSoup
from iso639 import Lang
from PIL import Image
from PySide6 import QtCore, QtGui

from ocr_result_block import OCRResultBlock
from ocr_result_line import OCRResultLine
from ocr_result_paragraph import OCRResultParagraph
from ocr_result_word import OCRResultWord


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

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False) -> list[OCRResultBlock] | None:
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

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False) -> list[OCRResultBlock] | None:
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

        # ret = pytesseract.image_to_data(self.pixmap_to_pil(image), config='--psm 6', output_type=pytesseract.Output.DICT)

        # text = ''

        # line = 0
        # last_line = line

        # for i in range(len(ret['level'])):
        #     line = ret['line_num'][i]

        #     if line != last_line:
        #         text += '\n'
        #         last_line = line

        #     if ret['level'][i] == 5:
        #         text += ret['text'][i] + ' '

        # print(text)

        if raw:
            image_cv2 = numpy.array(image.toImage().copy().bits()).reshape((image.height(), image.width(), 4))

            blur = cv2.GaussianBlur(image_cv2, (3, 3), 0)
            sat = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)[:, :, 1]
            thresh = cv2.threshold(sat, 50, 255, cv2.THRESH_BINARY)[1]

            gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
            otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1000, 1))
            dilate = cv2.dilate(otsu, kernel, iterations=2)

            # dilate = cv2.bitwise_not(dilate)

            cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]

            paragraph = OCRResultParagraph()

            for c in reversed(cnts):
                x, y, w, h = cv2.boundingRect(c)

                line_str = pytesseract.image_to_string(self.pixmap_to_pil(image.copy(x, y, w, h)), config='-c preserve_interword_spaces=1 --psm 7').strip()

                # ar = w / float(h)
                # # if ar < 5:
                # cv2.drawContours(image_cv2, [c], -1, (255, 0, 0), -1)

            # lines = pytesseract.image_to_string(self.pixmap_to_pil(image), config='-c preserve_interword_spaces=1 --psm 4').splitlines()

            # paragraph = OCRResultParagraph()

            # for line_str in lines:
                if line_str:
                    word = OCRResultWord()
                    word.text = line_str

                    line = OCRResultLine()
                    line.words.append(word)

                    paragraph.lines.append(line)

            block = OCRResultBlock(image.size(), px_per_mm)
            block.font = QtGui.QFontDatabase().systemFont(QtGui.QFontDatabase().SystemFont.FixedFont)
            block.paragraphs.append(paragraph)

            return [block]
        else:
            hocr = pytesseract.image_to_pdf_or_hocr(self.pixmap_to_pil(image), extension='hocr', lang=language.pt2t)

            if isinstance(hocr, bytes):
                return self.parse_hocr(hocr, image.size(), px_per_mm)


class OCREngineManager():
    def __init__(self, engines=[]) -> None:
        self.engines = engines
        self.current_engine = engines[-1]

    def get_current_engine(self) -> OCREngine:
        return self.current_engine
