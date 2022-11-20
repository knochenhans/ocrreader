from PySide6 import QtCore, QtGui

from hocrdata import HOCR_Data
from ocr_result_paragraph import OCRResultParagraph
from ocr_result_word import OCRResultWord


class OCRResultBlock(HOCR_Data):
    def __init__(self, image_size: QtCore.QSize = QtCore.QSize(), px_per_mm: float = 0.0, block=None):
        self.paragraphs = []
        self.image_size = image_size
        self.px_per_mm = px_per_mm
        if block:
            super().__init__(block['title'])

            for p in block.find_all('p', class_='ocr_par'):
                self.paragraphs.append(OCRResultParagraph(p))
        else:
            super().__init__()

        # Store box properties from box editor
        #self.properties = properties

    def write(self, file: QtCore.QDataStream) -> None:
        file.writeInt16(len(self.paragraphs))
        for paragraph in self.paragraphs:
            paragraph.write(file)

        file.writeQVariant(self.image_size)
        file.writeFloat(self.px_per_mm)

    def read(self, file: QtCore.QDataStream):
        paragraphs_count = file.readInt16()
        for p in range(paragraphs_count):
            paragraph = OCRResultParagraph()
            paragraph.read(file)

        self.image_size = file.readQVariant()
        self.px_per_mm = file.readFloat()

    def get_words(self) -> list[OCRResultWord]:
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
                    # cursor.insertText(' ')
                    cursor.insertText('\n')
            if p < (len(self.paragraphs) - 1):
                cursor.insertText('\n\n')

        return document

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance (ignore block itself)'''

        # self.bbox.translated(distance)

        for paragraph in self.paragraphs:
            paragraph.translate(distance)
