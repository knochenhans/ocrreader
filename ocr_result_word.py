from PySide6 import QtCore

from hocr_data import HOCR_Data


class OCRResultWord(HOCR_Data):
    def __init__(self, word=None):
        self.text = ''
        self.confidence = 0

        if word:
            title_data = word['title']
            super().__init__(title_data)
            self.text = word.get_text()

            data_lines = title_data.split('; ')

            for data_line in data_lines:
                tokens = data_line.split(' ')

                if tokens[0] == 'x_wconf':
                    self.confidence = int(tokens[1])
        else:
            super().__init__()

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

    def write(self, file: QtCore.QDataStream):
        file.writeQVariant(self.bbox)
        file.writeString(self.text)
        file.writeInt16(self.confidence)

    def read(self, file: QtCore.QDataStream):
        self.bbox = file.readQVariant()
        self.text = file.readString()
        self.confidence = file.readInt16()
