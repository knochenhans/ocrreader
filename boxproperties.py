from enum import Enum, auto

from iso639 import Lang
from PySide6 import QtCore, QtGui


class BOX_PROPERTY_TYPE(Enum):
    TEXT = auto()
    IMAGE = auto()


class BoxProperties():
    def __init__(self, order=0, rect=QtCore.QRect(), type: BOX_PROPERTY_TYPE = BOX_PROPERTY_TYPE.TEXT, text=QtGui.QTextDocument(), language: Lang = Lang('English'), ocr_block=None, words: list = []):
        self.order = order
        self.rect = rect
        self.type = type
        self.text = text
        self.language = language
        self.recognized = False
        self.ocr_block = ocr_block
        self.words = words
