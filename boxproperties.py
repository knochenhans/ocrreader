from enum import Enum, auto

from iso639 import Lang
from PySide6 import QtCore, QtGui

from ocr_result_block import OCRResultBlock
from ocr_result_word import OCRResultWord


class BOX_PROPERTY_TYPE(Enum):
    TEXT = auto()
    IMAGE = auto()


class BoxProperties():
    def __init__(self, order=0, rect=QtCore.QRect(), type: BOX_PROPERTY_TYPE = BOX_PROPERTY_TYPE.TEXT, text=QtGui.QTextDocument(), language: Lang = Lang('English'), ocr_result_block=OCRResultBlock(), words: list = None):
        self.order = order
        self.rect = rect
        self.type = type
        self.text = text
        self.language = language
        self.recognized = False
        self.ocr_result_block = ocr_result_block
        # self.test = QtGui.QTextDocument('test')

        self.words = words

        if self.words == None:
            self.words = []

    def write(self, file: QtCore.QDataStream) -> None:
        file.writeInt16(self.order)
        file.writeQVariant(self.rect)
        file.writeInt16(self.type.value)
        file.writeString(self.text.toHtml())
        file.writeString(self.language.name)
        file.writeBool(self.recognized)

        self.ocr_result_block.write(file)

        file.writeInt16(len(self.words))
        for word in self.words:
            word.write(file)

    def read(self, file: QtCore.QDataStream):
        self.order = file.readInt16()
        self.rect = file.readQVariant()
        self.type = BOX_PROPERTY_TYPE(file.readInt16())
        self.text = QtGui.QTextDocument()
        self.text.setHtml(file.readString())

        if not self.text:
            self.text = QtGui.QTextDocument()

        self.language = Lang(file.readString())
        self.recognized = file.readBool()

        self.ocr_result_block = OCRResultBlock()
        self.ocr_result_block.read(file)

        word_count = file.readInt16()

        for w in range(word_count):
            word = OCRResultWord()
            word.read(file)
            self.words.append(word)
