import io
import re

import pytesseract
from bs4 import BeautifulSoup, Tag
from iso639 import Lang
from PIL import Image
from PySide6 import QtCore, QtGui
from pytesseract import Output


class HOCR_Data():
    def __init__(self, title_data: str) -> None:
        self.bbox = QtCore.QRect()

        data_lines = title_data.split('; ')

        for data_line in data_lines:
            tokens = data_line.split(' ')

            if tokens[0] == 'bbox':
                self.bbox = QtCore.QRect(int(tokens[1]), int(tokens[2]), int(tokens[3]) - int(tokens[1]), int(tokens[4]) - int(tokens[2]))

    def translate(self, distance: QtCore.QPoint) -> None:
        pass


class OCRWord(HOCR_Data):
    def __init__(self, word):
        title_data = word['title']
        super().__init__(title_data)
        self.text = word.get_text()
        self.confidence = 0

        data_lines = title_data.split('; ')

        for data_line in data_lines:
            tokens = data_line.split(' ')

            if tokens[0] == 'x_wconf':
                self.confidence = int(tokens[1])

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)


class OCRLine(HOCR_Data):
    def __init__(self, line):
        title_data = line['title']
        super().__init__(title_data)

        self.words = []
        self.x_size = 0.0
        self.baseline = ()

        data_lines = title_data.split('; ')

        for data_line in data_lines:
            tokens = data_line.split(' ')

            if tokens[0] == 'x_size':
                self.x_size = float(tokens[1])
            elif tokens[0] == 'baseline':
                self.baseline = (float(tokens[1]), int(tokens[2]))

        for word in line.find_all('span', class_='ocrx_word'):
            self.words.append(OCRWord(word))

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

        for word in self.words:
            word.translate(distance)


class OCRParagraph(HOCR_Data):
    def __init__(self, paragraph):
        super().__init__(paragraph['title'])
        self.lines = []

        for line in paragraph.find_all('span', class_='ocr_line'):
            self.lines.append(OCRLine(line))

    def get_avg_height(self) -> int:
        sum_height = 0

        for line in self.lines:
            sum_height += line.x_size

        return round(sum_height / len(self.lines))

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

        for line in self.lines:
            line.translate(distance)


class OCRBlock(HOCR_Data):
    def __init__(self, block=None):
        self.paragraphs = []
        if block:
            super().__init__(block['title'])

            for p in block.find_all('p', class_='ocr_par'):
                self.paragraphs.append(OCRParagraph(p))

    def get_words(self) -> list[OCRWord]:
        '''Get list of words'''
        words = []

        for p in self.paragraphs:
            for l in p.lines:
                words += l.words
        return words

    def get_text(self, diagnostics=False) -> QtGui.QTextDocument:
        '''Get text as QTextDocument'''
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        for p, paragraph in enumerate(self.paragraphs):
            block_format = QtGui.QTextBlockFormat()
            # block_format.setBottomMargin(15.0)
            cursor.setBlockFormat(block_format)
            # TODO: Make this dependent on image DPI

            height = 297 / 2310 * paragraph.get_avg_height() * 3

            format.setFontPointSize(round(height))
            cursor.setCharFormat(format)
            # cursor.insertBlock(block_format)
            # cursor.deletePreviousChar()

            for l, line in enumerate(paragraph.lines):
                for w, word in enumerate(line.words):
                    if diagnostics:
                        if word.confidence < 90:
                            format.setBackground(QtGui.QColor(255, 0, 0, (1 - (word.confidence / 100)) * 200))
                        cursor.setCharFormat(format)

                    cursor.insertText(word.text)
                    if w < (len(line.words) - 1):
                        format.clearBackground()
                        cursor.setCharFormat(format)
                        cursor.insertText(' ')
                if l < (len(paragraph.lines) - 1):
                    cursor.insertText(' ')
                #     cursor.insertText('\n')
            if p < (len(self.paragraphs) - 1):
                cursor.insertText('\n\n')

        return document

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance (ignore block itself)'''

        # self.bbox.translated(distance)

        for paragraph in self.paragraphs:
            paragraph.translate(distance)


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

    def read_plain_text(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> str | None:
        return None

    def read(self, image: QtGui.QPixmap, language: Lang = Lang('English'), dpi: float = 72.0) -> OCRBlock | None:
        return None

# TODO: Implement https://github.com/sirfz/tesserocr


class OCREngineTesseract(OCREngine):
    def __init__(self):
        super().__init__('Tesseract')
        self.languages = pytesseract.get_languages()
        # self.languages = tesserocr.get_languages()[1]

    def parse_hocr(self, hocr: bytes) -> list[OCRBlock]:
        soup = BeautifulSoup(hocr.decode(), 'html.parser')

        blocks = []

        for div in soup.find_all('div', class_='ocr_carea'):
            blocks.append(OCRBlock(div))

        # Add safety margin sometimes needed for correct recognition
        margin = 5

        for block in blocks:
            block.bbox.adjust(-margin, -margin, margin, margin)

        return blocks

    def read(self, image: QtGui.QPixmap, language: Lang = Lang('English'), dpi: float = 72.0) -> list[OCRBlock] | None:
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
            return self.parse_hocr(hocr)


class OCREngineManager():
    def __init__(self, engines=[]) -> None:
        self.engines = engines
        self.current_engine = engines[-1]

    def get_current_engine(self) -> OCREngine:
        return self.current_engine
