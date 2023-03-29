from dataclasses import dataclass, field
from enum import Enum, auto

from iso639 import Lang
from PySide6 import QtCore, QtGui

from ocr_engine.ocr_results import OCRResultBlock, OCRResultWord


class BOX_DATA_TYPE(Enum):
    TEXT = auto()
    IMAGE = auto()


@dataclass
class BoxData():
    order: int = 0
    rect: QtCore.QRect = QtCore.QRect()
    type: BOX_DATA_TYPE = BOX_DATA_TYPE.TEXT
    text: QtGui.QTextDocument = QtGui.QTextDocument()
    language: Lang = Lang('English')
    ocr_result_block: OCRResultBlock = OCRResultBlock()
    tag: str = ''
    class_: str = ''
    export_enabled: bool = True
    recognized: bool = False

    words: list[OCRResultWord] = field(default_factory=list)

    def write(self, file: QtCore.QDataStream) -> None:
        file.writeInt16(self.order)
        file.writeQVariant(self.rect)
        file.writeInt16(self.type.value)
        file.writeString(self.text.toHtml())
        file.writeString(self.language.name)
        file.writeBool(self.recognized)
        file.writeString(self.tag)
        file.writeString(self.class_)
        file.writeBool(self.export_enabled)

        self.ocr_result_block.write(file)

        # file.writeInt16(len(self.words))
        # for word in self.words:
        #     word.write(file)

    def read(self, file: QtCore.QDataStream):
        self.order = file.readInt16()
        self.rect = file.readQVariant()
        self.type = BOX_DATA_TYPE(file.readInt16())
        self.text = QtGui.QTextDocument()
        self.text.setHtml(file.readString())

        if not self.text:
            self.text = QtGui.QTextDocument()

        self.language = Lang(file.readString())
        self.recognized = file.readBool()
        self.tag = file.readString()
        self.class_ = file.readString()
        self.export_enabled = file.readBool()

        self.ocr_result_block = OCRResultBlock()
        self.ocr_result_block.read(file)

    def get_paragraphs(self) -> list:
        paragraphs: list[list[QtGui.QTextFragment]] = []

        block = self.text.begin()

        while block.isValid():
            frag_it = next(block.begin())

            while True:
                fragments: list[QtGui.QTextFragment] = []

                for i in frag_it:
                    fragments.append(i.fragment())
                    next(i)

                try:
                    next(frag_it)
                except (StopIteration):
                    # End of paragraph detected
                    paragraphs.append(fragments)
                    break

            block = block.next()

        return paragraphs
