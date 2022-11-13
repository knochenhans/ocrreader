from PySide6 import QtCore

from hocrdata import HOCR_Data


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


