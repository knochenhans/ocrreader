from iso639 import Lang
from PySide6 import QtCore, QtGui

from document_helper import DocumentHelper
from hocr_data import HOCR_Data
from ocr_result_paragraph import OCRResultParagraph
from ocr_result_word import OCRResultWord


class OCRResultBlock(HOCR_Data):
    def __init__(self, image_size: QtCore.QSize = QtCore.QSize(), px_per_mm: float = 0.0, block=None, language: Lang = Lang('English')):
        self.paragraphs = []
        self.image_size = image_size
        self.px_per_mm = px_per_mm
        self.language = language
        self.font = QtGui.QFontDatabase().systemFont(QtGui.QFontDatabase().SystemFont.GeneralFont)
        self.foreground_color = QtGui.QColorConstants.Svg.black
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

    def get_avg_confidence(self) -> float:
        confidence = 0
        avg_confidence = confidence

        words = self.get_words()

        if words:
            for word in words:
                confidence += word.confidence
            avg_confidence = confidence / len(words)

        return avg_confidence

    def get_text(self, diagnostics: bool = False, remove_hyphens=False) -> QtGui.QTextDocument:
        '''Get text as QTextDocument'''
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        for p, paragraph in enumerate(self.paragraphs):
            if paragraph.lines:
                block_format = QtGui.QTextBlockFormat()
                # block_format.setBottomMargin(15.0)
                cursor.setBlockFormat(block_format)

                height = self.px_per_mm * paragraph.get_avg_height() * 3

                format.setFont(self.font)
                format.setFontPointSize(round(height))
                format.setForeground(self.foreground_color)
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
                        format.clearBackground()
                        cursor.setCharFormat(format)
                        if w < (len(line.words) - 1):
                            cursor.insertText(' ')
                    if l < (len(paragraph.lines) - 1):
                        # cursor.insertText(' ')
                        cursor.insertText('\n')
                if p < (len(self.paragraphs) - 1):
                    cursor.insertText('\n\n')

        if remove_hyphens:
            document_helper = DocumentHelper(document, self.language.pt1)
            document = document_helper.remove_hyphens()

        return document

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance (ignore block itself)'''

        # self.bbox.translated(distance)

        for paragraph in self.paragraphs:
            paragraph.translate(distance)
