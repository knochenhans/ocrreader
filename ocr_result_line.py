from PySide6 import QtCore

from hocrdata import HOCR_Data
from ocr_result_word import OCRResultWord


class OCRResultLine(HOCR_Data):
    def __init__(self, line):
        title_data = line['title']
        super().__init__(title_data)

        self.words = []
        self.x_size = 0.0
        self.baseline = ()

        data_lines = title_data.split('; ')

        for data_line in data_lines:
            tokens = data_line.split(' ')

            if tokens[0] == 'x_size':
                self.x_size = float(tokens[1])
            elif tokens[0] == 'baseline':
                self.baseline = (float(tokens[1]), int(tokens[2]))

        for word in line.find_all('span', class_='ocrx_word'):
            self.words.append(OCRResultWord(word))

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

        for word in self.words:
            word.translate(distance)
