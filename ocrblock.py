from PySide6 import QtCore, QtGui

from boxproperties import BoxProperties
from hocrdata import HOCR_Data
from ocrparagraph import OCRParagraph
from ocrword import OCRWord


class OCRBlock(HOCR_Data):
    def __init__(self, image_size: QtCore.QSize, px_per_mm: float, properties: BoxProperties = BoxProperties(), block=None):
        self.paragraphs = []
        self.px_per_mm = px_per_mm
        self.image_size = image_size
        if block:
            super().__init__(block['title'])

            for p in block.find_all('p', class_='ocr_par'):
                self.paragraphs.append(OCRParagraph(p))

        # Store box properties from box editor
        self.properties = properties

    def get_words(self) -> list[OCRWord]:
        '''Get list of words'''
        words = []

        for p in self.paragraphs:
            for l in p.lines:
                words += l.words
        return words

    def get_text(self, diagnostics: bool = False) -> QtGui.QTextDocument:
        '''Get text as QTextDocument'''
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        for p, paragraph in enumerate(self.paragraphs):
            block_format = QtGui.QTextBlockFormat()
            # block_format.setBottomMargin(15.0)
            cursor.setBlockFormat(block_format)

            height = self.px_per_mm * paragraph.get_avg_height() * 3

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
