from abc import abstractmethod
from dataclasses import dataclass, field

from iso639 import Lang
from PySide6 import QtCore, QtGui

from document_helper import DocumentHelper


@dataclass
class OCRResult():
    bbox_rect: QtCore.QRect = QtCore.QRect()
    text: str = ''
    confidence: float = 0.0
    baseline: QtCore.QLine = QtCore.QLine()
    font_size: float = 0.0

    def set_bbox(self, bbox: tuple[int, int, int, int]):
        self.bbox_rect = QtCore.QRect(QtCore.QPoint(bbox[0], bbox[1]), QtCore.QPoint(bbox[2], bbox[3]))

    def set_baseline(self, baseline: tuple[tuple[int, int], tuple[int, int]]):
        self.baseline = QtCore.QLine(baseline[0][0], baseline[0][1], baseline[1][0], baseline[1][1])

    @abstractmethod
    def translate(self, distance: QtCore.QPoint) -> None:
        pass


@dataclass
class OCRResultWord(OCRResult):
    blanks_before: int = 0

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)


@dataclass
class OCRResultLine(OCRResult):
    words: list[OCRResultWord] = field(default_factory=list)

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)

        for word in self.words:
            word.translate(distance)


@dataclass
class OCRResultParagraph(OCRResult):
    lines: list[OCRResultLine] = field(default_factory=list)

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)

        for line in self.lines:
            line.translate(distance)


@dataclass
class OCRResultBlock(OCRResult):
    paragraphs: list[OCRResultParagraph] = field(default_factory=list)
    language: Lang = Lang('en')

    def get_document(self, diagnostics: bool = False, remove_hyphens=True) -> QtGui.QTextDocument:
        '''Get text as QTextDocument'''
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        # TODO: Set this via options
        diagnostics_threshold = 80.0

        for p, paragraph in enumerate(self.paragraphs):
            if paragraph.lines:
                block_format = QtGui.QTextBlockFormat()
                # block_format.setBottomMargin(15.0)
                cursor.setBlockFormat(block_format)
                # format.setFont(self.font)
                format.setFontPointSize(round(self.get_font_size()))
                # format.setForeground(self.foreground_color)
                cursor.setCharFormat(format)
                # cursor.insertBlock(block_format)
                # cursor.deletePreviousChar()

                for l, line in enumerate(paragraph.lines):
                    for w, word in enumerate(line.words):
                        if diagnostics:
                            if word.confidence < diagnostics_threshold:
                                format.setBackground(QtGui.QColor(255, 0, 0, int(1 - (word.confidence / 100)) * 200))
                            cursor.setCharFormat(format)

                        cursor.insertText(word.blanks_before * ' ')
                        cursor.insertText(word.text)
                        format.clearBackground()
                        cursor.setCharFormat(format)
                        # if w < (len(line.words) - 1):
                        #     cursor.insertText(' ')
                    if l < (len(paragraph.lines) - 1):
                        cursor.insertText('\n')
                if p < (len(self.paragraphs) - 1):
                    cursor.insertText('\n\n')

        if remove_hyphens:
            document_helper = DocumentHelper(document, self.language.pt1)
            document = document_helper.remove_hyphens()

        # TODO: Better to clone here?
        return document

    def get_words(self) -> list[OCRResultWord]:
        '''Get list of words'''
        words: list[OCRResultWord] = []

        for p in self.paragraphs:
            for l in p.lines:
                words += l.words
        return words

    def get_font_size(self) -> float:
        '''Get average font size of text in block'''

        font_sizes_sum = 0.0

        words = self.get_words()

        for word in words:
            font_sizes_sum += word.font_size

        return font_sizes_sum / len(words)

    def translate(self, distance: QtCore.QPoint) -> None:
        '''Translate coordinates by a distance (ignore block itself)'''

        # self.bbox.translated(distance)

        for paragraph in self.paragraphs:
            paragraph.translate(distance)

    def add_margin(self, margin: int) -> None:
        self.bbox_rect.adjust(-margin, -margin, margin, margin)
