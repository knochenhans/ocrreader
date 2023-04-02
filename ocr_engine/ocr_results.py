from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

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

    def write(self, file: QtCore.QDataStream):
        file.writeQVariant(self.bbox_rect)
        file.writeString(self.text)
        file.writeFloat(self.confidence)
        file.writeQVariant(self.baseline)
        file.writeFloat(self.font_size)

    def read(self, file: QtCore.QDataStream):
        self.bbox_rect = file.readQVariant()
        self.text = file.readString()
        self.confidence = file.readFloat()
        self.baseline = file.readQVariant()
        self.font_size = file.readFloat()


@dataclass
class OCRResultWord(OCRResult):
    blanks_before: int = 0

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)

    def write(self, file: QtCore.QDataStream):
        super().write(file)
        file.writeInt16(self.blanks_before)

    def read(self, file: QtCore.QDataStream):
        super().read(file)
        self.blanks_before = file.readInt16()


@dataclass
class OCRResultLine(OCRResult):
    words: list[OCRResultWord] = field(default_factory=list)

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)

        for word in self.words:
            word.translate(distance)

    def write(self, file: QtCore.QDataStream):
        super().write(file)
        file.writeInt16(len(self.words))

        for word in self.words:
            word.write(file)

    def read(self, file: QtCore.QDataStream):
        super().read(file)
        word_count = file.readInt16()

        for w in range(word_count):
            word = OCRResultWord()
            word.read(file)
            self.words.append(word)


@dataclass
class OCRResultParagraph(OCRResult):
    lines: list[OCRResultLine] = field(default_factory=list)

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox_rect.translated(distance)

        for line in self.lines:
            line.translate(distance)

    def write(self, file: QtCore.QDataStream):
        super().write(file)
        file.writeInt16(len(self.lines))

        for line in self.lines:
            line.write(file)

    def read(self, file: QtCore.QDataStream):
        super().read(file)
        line_count = file.readInt16()

        for l in range(line_count):
            line = OCRResultLine()
            line.read(file)
            self.lines.append(line)


# TODO: Unify this with BOX_DATA_TYPE
class OCR_RESULT_BLOCK_TYPE(Enum):
    UNKNOWN = auto()
    TEXT = auto()
    IMAGE = auto()
    H_LINE = auto()
    V_LINE = auto()


@dataclass
class OCRResultBlock(OCRResult):
    paragraphs: list[OCRResultParagraph] = field(default_factory=list)
    language: Lang = Lang('en')
    type: OCR_RESULT_BLOCK_TYPE = OCR_RESULT_BLOCK_TYPE.TEXT
    tag: str = ''
    class_: str = ''

    def get_document(self, diagnostics: bool = False, remove_hyphens=True) -> QtGui.QTextDocument:
        '''Get text as QTextDocument'''
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        app_name = 'OCR Reader'

        QtCore.QCoreApplication.setOrganizationName(app_name)
        QtCore.QCoreApplication.setOrganizationDomain(app_name)
        QtCore.QCoreApplication.setApplicationName(app_name)

        settings = QtCore.QSettings()


        value = settings.value('diagnostics_threshold', 80)

        if isinstance(value, str):
            diagnostics_threshold = int(value)

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
                        if l < (len(paragraph.lines) - 1):
                            # QChar::LineSeparator
                            cursor.insertText('\u2028')
                if p < (len(self.paragraphs) - 1):
                    # QChar::ParagraphSeparator
                    cursor.insertText('\u2029')

            if remove_hyphens:
                document_helper = DocumentHelper(document, self.language.pt1)
                document = document_helper.remove_hyphens()

        # TODO: Better to clone here?
        return document

    def write(self, file: QtCore.QDataStream) -> None:
        file.writeInt16(len(self.paragraphs))

        for paragraph in self.paragraphs:
            paragraph.write(file)

        file.writeString(self.language.name)
        file.writeInt16(self.type.value)
        file.writeString(self.tag)
        file.writeString(self.class_)

    def read(self, file: QtCore.QDataStream):
        paragraphs_count = file.readInt16()

        for p in range(paragraphs_count):
            paragraph = OCRResultParagraph()
            paragraph.read(file)
            self.paragraphs.append(paragraph)

        self.language = Lang(file.readString())
        self.type = OCR_RESULT_BLOCK_TYPE(file.readInt16())
        self.tag = file.readString()
        self.class_ = file.readString()

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

        return int(font_sizes_sum / len(words))

    def translate(self, distance: QtCore.QPoint) -> None:
        '''Translate coordinates by a distance (ignore block itself)'''

        # self.bbox.translated(distance)

        for paragraph in self.paragraphs:
            paragraph.translate(distance)

    def add_margin(self, margin: int) -> None:
        self.bbox_rect.adjust(-margin, -margin, margin, margin)
